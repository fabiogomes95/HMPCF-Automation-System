import { useEffect, useMemo, useRef, useState } from "react";
import {
  buscarPlanilhaMensal, buscarPlanilhaPlantao, excluirAtendimentoRepetido, atualizarRegistroAtendimento, mensagemErro,
  buscarAjustesPlanilha, salvarAjustesPlanilha,
} from "../services/api";
import { formatCPF, formatCNS, formatTelefone, parseDateFromDB, idsRepetidosPorPlantao } from "../utils";
import "./PlanilhaAtendimentos.css";

const LABEL_PROCEDENCIA = {
  SAMU: "SAMU",
  TROCA: "TROCA",
  OBS: "UBS",
  GUARDA: "GUARDA",
  NORMAL: "", // "em normal deixar em branco"
};

// Código de raça/cor padrão BPA-SUS (paciente.raca) -- "03" (parda) é o
// padrão quando a recepção não indica nada no boletim.
const LABEL_RACA = {
  "01": "BRANCA",
  "1": "BRANCA",
  "02": "PRETA",
  "2": "PRETA",
  "03": "PARDA",
  "3": "PARDA",
  "04": "AMARELA",
  "4": "AMARELA",
  "05": "INDÍGENA",
  "5": "INDÍGENA",
};

function formatRaca(raca) {
  if (!raca) return "—";
  return LABEL_RACA[raca] ?? raca;
}

// Mesma regra de turno/dia_referencia do backend (recepcao_service.py) --
// diurno 07h-18h59, noturno 19h-06h59 (referenciado pelo dia em que
// começou), sempre no horário de Brasília, não no fuso do navegador/PC.
function turnoVigenteInfo() {
  const partes = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", hour12: false,
  }).formatToParts(new Date());
  const obter = tipo => Number(partes.find(p => p.type === tipo)?.value);
  const ano = obter("year");
  const mes = obter("month");
  const dia = obter("day");
  const hora = obter("hour");

  let turno = "NOTURNO";
  let dataRef = new Date(ano, mes - 1, dia);
  if (hora >= 7 && hora < 19) {
    turno = "DIURNO";
  } else if (hora < 7) {
    dataRef = new Date(ano, mes - 1, dia - 1);
  }

  const anoRef = dataRef.getFullYear();
  const mesRef = String(dataRef.getMonth() + 1).padStart(2, "0");
  const diaRef = String(dataRef.getDate()).padStart(2, "0");

  return { turno, diaISO: `${anoRef}-${mesRef}-${diaRef}`, mesISO: `${anoRef}-${mesRef}` };
}

function formatHora(iso) {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function formatDiaReferencia(diaISO) {
  const [ano, mes, dia] = diaISO.split("-");
  return `${dia}/${mes}/${ano}`;
}

// Idade NA DATA do atendimento (não a idade atual) -- é isso que a planilha
// manual sempre registrou, já que é o dado relevante pro atendimento daquele dia.
function calcularIdadeEm(dtnascBR, dataReferencia) {
  const partes = (dtnascBR || "").split("/");
  if (partes.length !== 3) return "";
  const [diaStr, mesStr, anoStr] = partes;
  const nasc = new Date(Number(anoStr), Number(mesStr) - 1, Number(diaStr));
  if (Number.isNaN(nasc.getTime())) return "";

  let anos = dataReferencia.getFullYear() - nasc.getFullYear();
  let meses = dataReferencia.getMonth() - nasc.getMonth();
  let dias = dataReferencia.getDate() - nasc.getDate();
  if (dias < 0) {
    meses--;
    const mesAnterior = new Date(dataReferencia.getFullYear(), dataReferencia.getMonth(), 0);
    dias += mesAnterior.getDate();
  }
  if (meses < 0) {
    anos--;
    meses += 12;
  }

  if (anos > 0) return `${anos}`;
  if (meses > 0) return `${meses}`;
  return `${dias}`;
}

// Copia texto pro clipboard. `navigator.clipboard` só existe em contexto
// seguro (HTTPS ou localhost) -- a segunda máquina da recepção acessa por
// http://IP:8001 (não é contexto seguro), então cai no fallback via
// textarea + execCommand, que funciona em HTTP normal.
async function copiarTexto(texto) {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(texto);
      return true;
    } catch {
      // cai pro fallback abaixo
    }
  }
  const textarea = document.createElement("textarea");
  textarea.value = texto;
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch {
    ok = false;
  }
  document.body.removeChild(textarea);
  return ok;
}

// Agrupa a lista (já ordenada cronologicamente pelo backend) em blocos
// consecutivos de mesmo dia_referencia + turno, igual às linhas separadoras
// da planilha original ("PLANTAO DIURNO/NOTURNO DD/MM/YYYY").
function agruparPorPlantao(items) {
  const grupos = [];
  for (const item of items) {
    const ultimo = grupos[grupos.length - 1];
    if (ultimo && ultimo.dia_referencia === item.dia_referencia && ultimo.turno === item.turno) {
      ultimo.items.push(item);
    } else {
      grupos.push({ dia_referencia: item.dia_referencia, turno: item.turno, items: [item] });
    }
  }
  return grupos;
}

// Refresh rápido: a recepção copia os dados em tempo real. Só vale quando a
// tela está num plantão específico -- aí busca SÓ aquele plantão (~100-200
// linhas). Vendo o mês todo, cada refresh baixa ~6 mil linhas, então fica
// no intervalo lento.
const REFRESH_PLANTAO_MS = 4000;
const REFRESH_MES_MS = 30000;

function porHorario(a, b) {
  return new Date(a.data_atendimento) - new Date(b.data_atendimento);
}

// Ajustes manuais (ordem/hora) que a recepção faz na planilha -- só visual,
// guardados no servidor fora do banco (planilha_ajustes_service.py).
function chaveAjuste(diaReferencia, turno) {
  return `${diaReferencia}|${turno}`;
}

// Minutos desde o começo do plantão: no noturno, 01:00 vem depois de 23:00.
function minutosNoPlantao(hhmm, turno) {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m + (turno === "NOTURNO" && h < 7 ? 24 * 60 : 0);
}

// Ordem de um plantão: pelo registro (01, 02...); quem não tem registro
// entra pelo horário, logo depois de quem chegou antes dele. Se a recepção
// arrumou a ordem à mão, vale a dela -- paciente novo (que ainda não estava
// na ordem salva) entra logo depois de quem vem antes dele na ordem automática.
function ordenarPlantao(items, turno, ajuste) {
  const horas = ajuste?.horas || {};
  const minutos = new Map(items.map(i => [
    i.atendimento_id,
    minutosNoPlantao(horas[i.atendimento_id] ?? formatHora(i.data_atendimento), turno),
  ]));
  const t = item => minutos.get(item.atendimento_id);

  const lista = items.filter(i => i.registro != null).sort((a, b) => a.registro - b.registro || t(a) - t(b));
  const semRegistro = items.filter(i => i.registro == null).sort((a, b) => t(a) - t(b));
  for (const item of semRegistro) {
    let pos = 0;
    lista.forEach((outro, i) => { if (t(outro) <= t(item)) pos = i + 1; });
    lista.splice(pos, 0, item);
  }

  const ordemSalva = ajuste?.ordem;
  if (!ordemSalva?.length) return lista;
  const porId = new Map(lista.map(i => [i.atendimento_id, i]));
  const final = ordemSalva.filter(id => porId.has(id)).map(id => porId.get(id));
  const naLista = new Set(final);
  lista.forEach((item, idx) => {
    if (naLista.has(item)) return;
    let pos = 0;
    for (let j = idx - 1; j >= 0; j--) {
      const k = final.indexOf(lista[j]);
      if (k >= 0) { pos = k + 1; break; }
    }
    final.splice(pos, 0, item);
    naLista.add(item);
  });
  return final;
}

export default function PlanilhaAtendimentos() {
  // Ao abrir a página: mês/dia/turno já vêm no plantão vigente (evita
  // renderizar o mês inteiro de cara -- com ~6mil atendimentos/mês isso
  // travava a página). "Ver o mês todo" continua disponível trocando os
  // filtros manualmente (ver efeito abaixo).
  const [mes, setMes]         = useState(() => turnoVigenteInfo().mesISO);
  const [turnoFiltro, setTurnoFiltro] = useState(() => turnoVigenteInfo().turno);
  const [diaFiltro, setDiaFiltro]     = useState(() => turnoVigenteInfo().diaISO);
  const [pacienteFiltro, setPacienteFiltro] = useState("");
  const [items, setItems]     = useState([]);
  const [total, setTotal]     = useState(0);
  const [loading, setLoading] = useState(false);
  const [erro, setErro]       = useState("");
  const [copiadoId, setCopiadoId] = useState(null);
  const [excluidoMsg, setExcluidoMsg] = useState("");
  const [editRegId, setEditRegId]     = useState(null);
  const [editRegVal, setEditRegVal]   = useState("");
  const [ajustes, setAjustes]         = useState({});
  const [editHoraId, setEditHoraId]   = useState(null);
  const [editHoraVal, setEditHoraVal] = useState("");
  const primeiraCargaRef = useRef(true);
  const manterDiaRef = useRef(false);
  // Sobe a cada gravação: resposta de busca que saiu antes dela é descartada
  // (senão o refresh traria de volta a ordem antiga por alguns segundos).
  const versaoAjustesRef = useRef(0);

  async function carregarAjustes(ano, mesNum) {
    const versao = versaoAjustesRef.current;
    try {
      const res = await buscarAjustesPlanilha(ano, mesNum);
      if (versao === versaoAjustesRef.current) setAjustes(res.data);
    } catch {
      // sem os ajustes a planilha continua na ordem automática
    }
  }

  useEffect(() => {
    const [ano, mesNum] = mes.split("-").map(Number);
    if (!ano || !mesNum) return;
    setLoading(true);
    setErro("");
    if (primeiraCargaRef.current || manterDiaRef.current) {
      primeiraCargaRef.current = false;
      manterDiaRef.current = false;
    } else {
      setDiaFiltro("TODOS");
    }
    carregarAjustes(ano, mesNum);
    buscarPlanilhaMensal(ano, mesNum)
      .then(res => {
        setItems(res.data.items);
        setTotal(res.data.total);
      })
      .catch(() => {
        setItems([]);
        setTotal(0);
        setErro("Não foi possível carregar a planilha deste mês.");
      })
      .finally(() => setLoading(false));
  }, [mes]);

  // Auto-refresh silencioso — não reseta filtros. Pula quando a aba está em
  // segundo plano ou quando a chamada anterior ainda não voltou.
  const refreshEmAndamento = useRef(false);
  const plantaoFixo = diaFiltro !== "TODOS" && turnoFiltro !== "TODOS";
  useEffect(() => {
    const [ano, mesNum] = mes.split("-").map(Number);
    if (!ano || !mesNum) return;

    async function atualizar() {
      if (document.hidden || refreshEmAndamento.current) return;
      refreshEmAndamento.current = true;
      try {
        await carregarAjustes(ano, mesNum); // o outro computador pode ter mexido na ordem
        if (plantaoFixo) {
          // Troca só as linhas desse plantão; o resto do mês fica como está.
          const res = await buscarPlanilhaPlantao(diaFiltro, turnoFiltro);
          setItems(prev => {
            const outros = prev.filter(i => !(i.dia_referencia === diaFiltro && i.turno === turnoFiltro));
            const juntos = [...outros, ...res.data.items].sort(porHorario);
            setTotal(juntos.length);
            return juntos;
          });
        } else {
          const res = await buscarPlanilhaMensal(ano, mesNum);
          setItems(res.data.items);
          setTotal(res.data.total);
        }
      } catch {
        // silencioso -- tenta de novo no próximo ciclo
      } finally {
        refreshEmAndamento.current = false;
      }
    }

    const id = setInterval(atualizar, plantaoFixo ? REFRESH_PLANTAO_MS : REFRESH_MES_MS);
    return () => clearInterval(id);
  }, [mes, plantaoFixo, diaFiltro, turnoFiltro]);

  const diasDisponiveis = useMemo(() => {
    const vistos = new Set();
    const dias = [];
    for (const item of items) {
      if (!vistos.has(item.dia_referencia)) {
        vistos.add(item.dia_referencia);
        dias.push(item.dia_referencia);
      }
    }
    // Plantão que acabou de virar ainda não tem linha nenhuma -- o dia
    // selecionado precisa existir no filtro mesmo assim.
    if (diaFiltro !== "TODOS" && !vistos.has(diaFiltro)) {
      dias.push(diaFiltro);
      dias.sort();
    }
    return dias;
  }, [items, diaFiltro]);

  // Troca automática de plantão (07h e 19h): se a tela está no plantão
  // vigente, acompanha a virada. Se alguém escolheu outro plantão/dia pra
  // consultar, não mexe.
  const vigenteRef = useRef(turnoVigenteInfo());
  useEffect(() => {
    const id = setInterval(() => {
      const novo = turnoVigenteInfo();
      const antigo = vigenteRef.current;
      if (novo.diaISO === antigo.diaISO && novo.turno === antigo.turno) return;
      vigenteRef.current = novo;
      if (diaFiltro !== antigo.diaISO || turnoFiltro !== antigo.turno) return;
      if (novo.mesISO !== mes) {
        manterDiaRef.current = true; // virada de mês: não resetar o dia pra "Todos"
        setMes(novo.mesISO);
      }
      setDiaFiltro(novo.diaISO);
      setTurnoFiltro(novo.turno);
    }, 15000);
    return () => clearInterval(id);
  }, [diaFiltro, turnoFiltro, mes]);

  // Plantões completos e já na ordem certa -- a ordem é calculada antes do
  // filtro de paciente, pra mover alguém sempre considerar o plantão inteiro.
  const gruposOrdenados = useMemo(() => {
    const doFiltro = items.filter(item =>
      (turnoFiltro === "TODOS" || item.turno === turnoFiltro) &&
      (diaFiltro === "TODOS" || item.dia_referencia === diaFiltro));
    return agruparPorPlantao(doFiltro).map(g => ({
      ...g,
      items: ordenarPlantao(g.items, g.turno, ajustes[chaveAjuste(g.dia_referencia, g.turno)]),
    }));
  }, [items, turnoFiltro, diaFiltro, ajustes]);

  const termoPaciente = pacienteFiltro.trim().toUpperCase();
  const grupos = useMemo(() => {
    if (!termoPaciente) return gruposOrdenados;
    const termoDigitos = termoPaciente.replace(/\D/g, "");
    return gruposOrdenados
      .map(g => ({
        ...g,
        items: g.items.filter(item => {
          const nome = (item.nome || "").toUpperCase();
          const cpf  = (item.num_cpf || "").replace(/\D/g, "");
          return nome.includes(termoPaciente) || (termoDigitos.length > 0 && cpf.includes(termoDigitos));
        }),
      }))
      .filter(g => g.items.length > 0);
  }, [gruposOrdenados, termoPaciente]);
  const totalVisivel = grupos.reduce((soma, g) => soma + g.items.length, 0);

  // Calculado sobre o mês todo (não só o filtrado), pra marcação não mudar
  // conforme o filtro de paciente/dia.
  const repetidos = useMemo(() => idsRepetidosPorPlantao(items), [items]);

  async function handleCopiarLinha(item, linha) {
    const ok = await copiarTexto(linha);
    if (!ok) return;
    setCopiadoId(item.atendimento_id);
    setTimeout(() => {
      setCopiadoId(id => (id === item.atendimento_id ? null : id));
    }, 1500);
  }

  async function handleSalvarRegistro(item) {
    try {
      await atualizarRegistroAtendimento(item.atendimento_id, editRegVal);
      setEditRegId(null);
      const [ano, mesNum] = mes.split("-").map(Number);
      const res = await buscarPlanilhaMensal(ano, mesNum);
      setItems(res.data.items);
      setTotal(res.data.total);
    } catch (err) {
      setExcluidoMsg(mensagemErro(err, "Erro ao salvar registro."));
      setTimeout(() => setExcluidoMsg(""), 3000);
    }
  }

  // Grava na hora na tela e depois no servidor; se falhar, avisa e o próximo
  // refresh traz de volta o que está salvo.
  async function gravarAjuste(grupo, novo) {
    const chave = chaveAjuste(grupo.dia_referencia, grupo.turno);
    versaoAjustesRef.current += 1;
    setAjustes(prev => {
      const proximo = { ...prev };
      if (novo.ordem.length || Object.keys(novo.horas).length) proximo[chave] = novo;
      else delete proximo[chave];
      return proximo;
    });
    try {
      await salvarAjustesPlanilha(grupo.dia_referencia, grupo.turno, novo.ordem, novo.horas);
      versaoAjustesRef.current += 1;
    } catch (err) {
      setExcluidoMsg(mensagemErro(err, "Não foi possível salvar o ajuste da planilha."));
      setTimeout(() => setExcluidoMsg(""), 3000);
    }
  }

  function ajusteDo(grupo) {
    return ajustes[chaveAjuste(grupo.dia_referencia, grupo.turno)] || { ordem: [], horas: {} };
  }

  function handleMover(grupo, indice, passo) {
    const ids = grupo.items.map(i => i.atendimento_id);
    const destino = indice + passo;
    if (destino < 0 || destino >= ids.length) return;
    [ids[indice], ids[destino]] = [ids[destino], ids[indice]];
    gravarAjuste(grupo, { ...ajusteDo(grupo), ordem: ids });
  }

  function handleSalvarHora(grupo, item) {
    const horas = { ...ajusteDo(grupo).horas };
    // Vazio ou igual à do sistema: volta a mostrar a hora original.
    if (!editHoraVal || editHoraVal === formatHora(item.data_atendimento)) delete horas[item.atendimento_id];
    else horas[item.atendimento_id] = editHoraVal;
    setEditHoraId(null);
    gravarAjuste(grupo, { ...ajusteDo(grupo), horas });
  }

  function handleOrdemAutomatica(grupo) {
    if (!window.confirm("Voltar este plantão para a ordem automática (pelo registro e, sem registro, pela hora)?")) return;
    gravarAjuste(grupo, { ...ajusteDo(grupo), ordem: [] });
  }

  async function handleExcluirDuplicata(item) {
    const fica = repetidos.get(item.atendimento_id);
    if (!window.confirm(
      `Excluir este atendimento duplicado de ${item.nome || "?"}?\n` +
      `Sai:  ${formatHora(item.data_atendimento)} — Registro: ${item.registro ?? "—"}\n` +
      `Fica: ${fica ? formatHora(fica.data_atendimento) : "?"} — Registro: ${fica?.registro ?? "—"} (mais novo)`
    )) return;
    try {
      await excluirAtendimentoRepetido(item.atendimento_id);
      const [ano, mesNum] = mes.split("-").map(Number);
      const res = await buscarPlanilhaMensal(ano, mesNum);
      setItems(res.data.items);
      setTotal(res.data.total);
      setExcluidoMsg("Atendimento excluído.");
      setTimeout(() => setExcluidoMsg(""), 3000);
    } catch (err) {
      setExcluidoMsg(mensagemErro(err, "Erro ao excluir."));
      setTimeout(() => setExcluidoMsg(""), 3000);
    }
  }

  return (
    <div className="planilha">
      <div className="planilha-header no-print">
        <div className="planilha-titulo">
          <h2>Planilha de Atendimentos</h2>
          {!loading && (
            <span className="planilha-total">
              {totalVisivel} de {total} atendimento{total !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        <div className="planilha-filtros">
          <label className="planilha-filtro-campo">
            Mês
            <input
              type="month"
              value={mes}
              onChange={e => setMes(e.target.value)}
            />
          </label>

          <label className="planilha-filtro-campo">
            Turno
            <select value={turnoFiltro} onChange={e => setTurnoFiltro(e.target.value)}>
              <option value="TODOS">Todos</option>
              <option value="DIURNO">Diurno (07h-18h59)</option>
              <option value="NOTURNO">Noturno (19h-06h59)</option>
            </select>
          </label>

          <label className="planilha-filtro-campo">
            Dia
            <select value={diaFiltro} onChange={e => setDiaFiltro(e.target.value)}>
              <option value="TODOS">Todos</option>
              {diasDisponiveis.map(dia => (
                <option key={dia} value={dia}>{formatDiaReferencia(dia)}</option>
              ))}
            </select>
          </label>

          <label className="planilha-filtro-campo">
            Paciente
            <input
              type="text"
              placeholder="Nome ou CPF"
              value={pacienteFiltro}
              onChange={e => {
                setPacienteFiltro(e.target.value);
                if (e.target.value.trim()) setDiaFiltro("TODOS");
              }}
              style={{ padding: "0.25rem 0.4rem", fontSize: "0.88rem", border: "1px solid #ccc", borderRadius: "4px" }}
            />
          </label>
        </div>
      </div>

      <div className="planilha-tabela-wrap">
        {excluidoMsg && <div className="planilha-msg-ok no-print">{excluidoMsg}</div>}
        {loading && <div className="planilha-loading">Carregando...</div>}
        {erro && <div className="planilha-erro">{erro}</div>}

        {!loading && !erro && grupos.length === 0 && (
          <div className="planilha-vazio">Nenhum atendimento encontrado para este filtro.</div>
        )}

        {!loading && !erro && grupos.map(grupo => {
          const ajuste = ajusteDo(grupo);
          const podeMover = !termoPaciente; // com filtro de paciente o plantão aparece pela metade
          return (
          <div className="planilha-grupo" key={`${grupo.dia_referencia}-${grupo.turno}`}>
            <div className={`planilha-plantao planilha-plantao-${grupo.turno.toLowerCase()}`}>
              PLANTÃO {grupo.turno} — {formatDiaReferencia(grupo.dia_referencia)}
              <span className="planilha-plantao-acoes">
                {ajuste.ordem.length > 0 && (
                  <button
                    type="button"
                    className="btn-ordem-automatica no-print"
                    onClick={() => handleOrdemAutomatica(grupo)}
                    title="A ordem deste plantão foi arrumada à mão"
                  >↺ Ordem automática</button>
                )}
                <span className="planilha-plantao-contador">{grupo.items.length} atendimento{grupo.items.length !== 1 ? "s" : ""}</span>
              </span>
            </div>

            <div className="planilha-tabela-scroll">
            <table className="planilha-tabela">
              <thead>
                <tr>
                  <th style={{ width: 36 }} className="no-print"></th>
                  {podeMover && <th style={{ width: 30 }} className="no-print" title="Mudar a posição na planilha"></th>}
                  <th style={{ width: 60 }}>Registro</th>
                  <th>Nome</th>
                  <th style={{ width: 90 }}>Nascimento</th>
                  <th style={{ width: 90 }}>Idade</th>
                  <th style={{ width: 50 }}>Sexo</th>
                  <th style={{ width: 70 }}>Cor</th>
                  <th style={{ width: 100 }}>Cidade</th>
                  <th style={{ width: 60 }}>Hora</th>
                  <th style={{ width: 120 }}>CPF</th>
                  <th style={{ width: 150 }}>SUS</th>
                  <th style={{ width: 70 }}>Aba</th>
                  <th>Endereço</th>
                  <th style={{ width: 120 }}>Telefone</th>
                </tr>
              </thead>
              <tbody>
                {grupo.items.map((item, indice) => {
                  const duplicata = repetidos.has(item.atendimento_id);
                  const dtnascBR = parseDateFromDB(item.dtnasc);
                  const horaSistema = formatHora(item.data_atendimento);
                  const horaAjustada = ajuste.horas[item.atendimento_id];
                  const hora = horaAjustada ?? horaSistema;
                  const campos = [
                    item.registro ?? "",
                    item.nome || "",
                    dtnascBR || "",
                    dtnascBR ? calcularIdadeEm(dtnascBR, new Date(item.data_atendimento)) : "",
                    item.sexo || "",
                    formatRaca(item.raca) === "—" ? "" : formatRaca(item.raca),
                    item.cidade || "",
                    hora,
                    item.num_cpf ? formatCPF(item.num_cpf) : "",
                    item.cns ? formatCNS(item.cns) : "",
                    LABEL_PROCEDENCIA[item.procedencia] ?? item.procedencia ?? "",
                    item.endereco || "",
                    item.telefone ? formatTelefone(item.telefone) : "",
                  ];
                  const linhaCopia = campos.join("\t");
                  return (
                    <tr key={item.atendimento_id} className={duplicata ? "linha-duplicata" : ""}>
                      <td className="cel-copiar no-print">
                        {duplicata ? (
                          <button
                            type="button"
                            className="btn-excluir-duplicata"
                            onClick={() => handleExcluirDuplicata(item)}
                            title="Excluir duplicata"
                          >✕</button>
                        ) : (
                          <button
                            type="button"
                            className="btn-copiar-linha"
                            onClick={() => handleCopiarLinha(item, linhaCopia)}
                            title="Copiar linha (cola direto nas colunas do Excel)"
                          >
                            {copiadoId === item.atendimento_id ? "✓" : "⧉"}
                          </button>
                        )}
                      </td>
                      {podeMover && (
                        <td className="cel-mover no-print">
                          <button type="button" onClick={() => handleMover(grupo, indice, -1)} disabled={indice === 0} title="Subir">▲</button>
                          <button type="button" onClick={() => handleMover(grupo, indice, 1)} disabled={indice === grupo.items.length - 1} title="Descer">▼</button>
                        </td>
                      )}
                      <td>
                        {editRegId === item.atendimento_id ? (
                          <span className="cel-registro-edit no-print">
                            <input
                              type="number"
                              min="1"
                              value={editRegVal}
                              onChange={e => setEditRegVal(e.target.value)}
                              onKeyDown={e => { if (e.key === "Enter") handleSalvarRegistro(item); if (e.key === "Escape") setEditRegId(null); }}
                              autoFocus
                            />
                            <button className="btn-salvar-registro" onClick={() => handleSalvarRegistro(item)}>✓</button>
                            <button className="btn-cancelar-registro" onClick={() => setEditRegId(null)}>✕</button>
                          </span>
                        ) : (
                          <span
                            className="registro-editavel"
                            title="Clique para editar"
                            onClick={() => { setEditRegId(item.atendimento_id); setEditRegVal(item.registro != null ? String(item.registro) : ""); }}
                          >
                            {item.registro ?? "—"}
                          </span>
                        )}
                      </td>
                      <td className="cel-nome">
                        {item.nome || "—"}
                        {duplicata && (
                          <span
                            className="badge-duplicata no-print"
                            title={`Registrado de novo às ${formatHora(repetidos.get(item.atendimento_id).data_atendimento)} — fica o registro mais novo`}
                          >
                            REPETIDO
                          </span>
                        )}
                      </td>
                      <td>{dtnascBR || "—"}</td>
                      <td>{dtnascBR ? calcularIdadeEm(dtnascBR, new Date(item.data_atendimento)) : "—"}</td>
                      <td>{item.sexo || "—"}</td>
                      <td>{formatRaca(item.raca)}</td>
                      <td>{item.cidade || "—"}</td>
                      <td>
                        {editHoraId === item.atendimento_id ? (
                          <span className="cel-registro-edit cel-hora-edit no-print">
                            <input
                              type="time"
                              value={editHoraVal}
                              onChange={e => setEditHoraVal(e.target.value)}
                              onKeyDown={e => { if (e.key === "Enter") handleSalvarHora(grupo, item); if (e.key === "Escape") setEditHoraId(null); }}
                              autoFocus
                            />
                            <button className="btn-salvar-registro" onClick={() => handleSalvarHora(grupo, item)}>✓</button>
                            <button className="btn-cancelar-registro" onClick={() => setEditHoraId(null)}>✕</button>
                          </span>
                        ) : (
                          <span
                            className={`registro-editavel${horaAjustada ? " hora-ajustada" : ""}`}
                            title={horaAjustada
                              ? `Hora ajustada na planilha (no sistema: ${horaSistema}). Clique para mudar; apague para voltar.`
                              : "Clique para ajustar a hora (só na planilha)"}
                            onClick={() => { setEditHoraId(item.atendimento_id); setEditHoraVal(hora); }}
                          >
                            {hora}
                          </span>
                        )}
                      </td>
                      <td>{item.num_cpf ? formatCPF(item.num_cpf) : "—"}</td>
                      <td>{item.cns ? formatCNS(item.cns) : "—"}</td>
                      <td className="cel-aba">{LABEL_PROCEDENCIA[item.procedencia] ?? item.procedencia ?? ""}</td>
                      <td className="cel-endereco">{item.endereco || "—"}</td>
                      <td>{item.telefone ? formatTelefone(item.telefone) : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            </div>
          </div>
          );
        })}
      </div>
    </div>
  );
}
