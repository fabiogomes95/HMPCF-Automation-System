import { useEffect, useMemo, useState } from "react";
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

function mesAtualISO() {
  const hoje = new Date();
  return `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, "0")}`;
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
  const [mes, setMes]         = useState(mesAtualISO());
  const [turnoFiltro, setTurnoFiltro] = useState("TODOS");
  const [diaFiltro, setDiaFiltro]     = useState("TODOS");
  const [items, setItems]     = useState([]);
  const [total, setTotal]     = useState(0);
  const [loading, setLoading] = useState(false);
  const [erro, setErro]       = useState("");

  useEffect(() => {
    const [ano, mesNum] = mes.split("-").map(Number);
    if (!ano || !mesNum) return;
    setLoading(true);
    setErro("");
    setDiaFiltro("TODOS");
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

            <table className="planilha-tabela">
              <thead>
                <tr>
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
                  return (
                    <tr key={item.atendimento_id}>
                      <td>{item.registro ?? "—"}</td>
                      <td className="cel-nome">{item.nome || "—"}</td>
                      <td>{dtnascBR || "—"}</td>
                      <td>{dtnascBR ? calcularIdadeEm(dtnascBR, new Date(item.data_atendimento)) : "—"}</td>
                      <td>{item.sexo || "—"}</td>
                      <td>{item.raca || "—"}</td>
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
        ))}
      </div>
    </div>
  );
}
