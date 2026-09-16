import { useEffect, useMemo, useRef, useState } from "react";
import { buscarPlanilhaMensal } from "../services/api";
import { formatCPF, formatCNS, formatTelefone, parseDateFromDB } from "../utils";
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

  if (anos > 0) return `${anos} ${anos === 1 ? "ANO" : "ANOS"}`;
  if (meses > 0) return `${meses} ${meses === 1 ? "MÊS" : "MESES"}`;
  return `${dias} ${dias === 1 ? "DIA" : "DIAS"}`;
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

export default function PlanilhaAtendimentos() {
  // Ao abrir a página: mês/dia/turno já vêm no plantão vigente (evita
  // renderizar o mês inteiro de cara -- com ~6mil atendimentos/mês isso
  // travava a página). "Ver o mês todo" continua disponível trocando os
  // filtros manualmente (ver efeito abaixo).
  const [mes, setMes]         = useState(() => turnoVigenteInfo().mesISO);
  const [turnoFiltro, setTurnoFiltro] = useState(() => turnoVigenteInfo().turno);
  const [diaFiltro, setDiaFiltro]     = useState(() => turnoVigenteInfo().diaISO);
  const [items, setItems]     = useState([]);
  const [total, setTotal]     = useState(0);
  const [loading, setLoading] = useState(false);
  const [erro, setErro]       = useState("");
  const [copiadoId, setCopiadoId] = useState(null);
  const primeiraCargaRef = useRef(true);

  useEffect(() => {
    const [ano, mesNum] = mes.split("-").map(Number);
    if (!ano || !mesNum) return;
    setLoading(true);
    setErro("");
    // Só reseta o filtro de dia quando o mês é trocado manualmente -- na
    // carga inicial o dia já vem pré-selecionado no plantão vigente.
    if (primeiraCargaRef.current) {
      primeiraCargaRef.current = false;
    } else {
      setDiaFiltro("TODOS");
    }
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

  const diasDisponiveis = useMemo(() => {
    const vistos = new Set();
    const dias = [];
    for (const item of items) {
      if (!vistos.has(item.dia_referencia)) {
        vistos.add(item.dia_referencia);
        dias.push(item.dia_referencia);
      }
    }
    return dias;
  }, [items]);

  const itemsFiltrados = useMemo(() => {
    return items.filter(item => {
      if (turnoFiltro !== "TODOS" && item.turno !== turnoFiltro) return false;
      if (diaFiltro !== "TODOS" && item.dia_referencia !== diaFiltro) return false;
      return true;
    });
  }, [items, turnoFiltro, diaFiltro]);

  const grupos = useMemo(() => agruparPorPlantao(itemsFiltrados), [itemsFiltrados]);

  async function handleCopiarLinha(item, linha) {
    const ok = await copiarTexto(linha);
    if (!ok) return;
    setCopiadoId(item.atendimento_id);
    setTimeout(() => {
      setCopiadoId(id => (id === item.atendimento_id ? null : id));
    }, 1500);
  }

  return (
    <div className="planilha">
      <div className="planilha-header no-print">
        <div className="planilha-titulo">
          <h2>Planilha de Atendimentos</h2>
          {!loading && (
            <span className="planilha-total">
              {itemsFiltrados.length} de {total} atendimento{total !== 1 ? "s" : ""}
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
        </div>
      </div>

      <div className="planilha-tabela-wrap">
        {loading && <div className="planilha-loading">Carregando...</div>}
        {erro && <div className="planilha-erro">{erro}</div>}

        {!loading && !erro && grupos.length === 0 && (
          <div className="planilha-vazio">Nenhum atendimento encontrado para este filtro.</div>
        )}

        {!loading && !erro && grupos.map(grupo => (
          <div className="planilha-grupo" key={`${grupo.dia_referencia}-${grupo.turno}`}>
            <div className={`planilha-plantao planilha-plantao-${grupo.turno.toLowerCase()}`}>
              PLANTÃO {grupo.turno} — {formatDiaReferencia(grupo.dia_referencia)}
              <span className="planilha-plantao-contador">{grupo.items.length} atendimento{grupo.items.length !== 1 ? "s" : ""}</span>
            </div>

            <div className="planilha-tabela-scroll">
            <table className="planilha-tabela">
              <thead>
                <tr>
                  <th style={{ width: 36 }} className="no-print"></th>
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
                {grupo.items.map(item => {
                  const dtnascBR = parseDateFromDB(item.dtnasc);
                  const campos = [
                    item.registro ?? "",
                    item.nome || "",
                    dtnascBR || "",
                    dtnascBR ? calcularIdadeEm(dtnascBR, new Date(item.data_atendimento)) : "",
                    item.sexo || "",
                    formatRaca(item.raca) === "—" ? "" : formatRaca(item.raca),
                    item.cidade || "",
                    formatHora(item.data_atendimento),
                    item.num_cpf ? formatCPF(item.num_cpf) : "",
                    item.cns ? formatCNS(item.cns) : "",
                    LABEL_PROCEDENCIA[item.procedencia] ?? item.procedencia ?? "",
                    item.endereco || "",
                    item.telefone ? formatTelefone(item.telefone) : "",
                  ];
                  const linhaCopia = campos.join("\t");
                  return (
                    <tr key={item.atendimento_id}>
                      <td className="cel-copiar no-print">
                        <button
                          type="button"
                          className="btn-copiar-linha"
                          onClick={() => handleCopiarLinha(item, linhaCopia)}
                          title="Copiar linha (cola direto nas colunas do Excel)"
                        >
                          {copiadoId === item.atendimento_id ? "✓" : "⧉"}
                        </button>
                      </td>
                      <td>{item.registro ?? "—"}</td>
                      <td className="cel-nome">{item.nome || "—"}</td>
                      <td>{dtnascBR || "—"}</td>
                      <td>{dtnascBR ? calcularIdadeEm(dtnascBR, new Date(item.data_atendimento)) : "—"}</td>
                      <td>{item.sexo || "—"}</td>
                      <td>{formatRaca(item.raca)}</td>
                      <td>{item.cidade || "—"}</td>
                      <td>{formatHora(item.data_atendimento)}</td>
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
        ))}
      </div>
    </div>
  );
}
