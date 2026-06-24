import HeaderHospital from "./HeaderHospital";
import { formatCPF, formatCNS, formatTelefone } from "../../utils";
import "./boletim.css";

const racasBoletim = [
  { cod: "01", label: "BRANCA" },
  { cod: "02", label: "PRETA" },
  { cod: "03", label: "PARDA" },
  { cod: "04", label: "AMARELA" },
  { cod: "05", label: "INDÍGENA" },
];

const civisLegado = [
  "SOLTEIRO", "CASADO", "UNIÃO ESTÁVEL", "DIVORCIADO", "VIÚVO",
];

const comorbidades = [
  "HAS", "DM", "DISLIPIDEMIA", "ETILISTA", "TABAGISTA", "OUTROS",
];

export default function BoletimA4({
  form = {},
  idade = "",
  atdInfo = {},
  onDataChange,
  onHoraChange,
  onRegistroChange,
  onCPFChange,
  onCNSChange,
  onDtnascChange,
  onTelChange,
  onRacaChange,
  onSexoChange,
  onFieldChange,
  cpfRef,
  erroCpf,
  erroCns,
  erroDtnasc,
  onFamilia,
}) {
  return (
    <div className="page">
      <form id="formBoletim">
        <HeaderHospital />

        {/* ─── Linha 1: Data / Hora / Registro ─── */}
        <div className="row top-border spacer-row">
          <div className="field campo-data">
            <label>DATA DE ATENDIMENTO:</label>
            <input type="text" value={atdInfo.data || ""} onChange={onDataChange} />
          </div>
          <div className="field campo-hora">
            <label>HORA:</label>
            <input type="text" value={atdInfo.hora || ""} onChange={onHoraChange} />
          </div>
          <div className="field campo-registro">
            <label>REGISTRO:</label>
            <input type="text" value={atdInfo.registro || ""} onChange={onRegistroChange} maxLength={4} />
          </div>
        </div>

        {/* ─── Linha 2: Nome completo ─── */}
        <div className="row top-border">
          <div className="field">
            <label>NOME COMPLETO:</label>
            <input type="text" name="nome" value={form.nome || ""} onChange={onFieldChange} />
          </div>
        </div>

        {/* ─── Linha 3: Nome Social ─── */}
        <div className="row">
          <div className="field">
            <label>NOME SOCIAL:</label>
            <input type="text" name="nome_social" value={form.nome_social || ""} onChange={onFieldChange} />
          </div>
        </div>

        {/* ─── Linha 4: Naturalidade / DN / Idade ─── */}
        <div className="row">
          <div className="field campo-naturalidade">
            <label>NATURALIDADE:</label>
            <input type="text" name="naturalidade" value={form.naturalidade || ""} onChange={onFieldChange} />
          </div>
          <div className="field campo-dn">
            <label>DN:</label>
            <input
              type="text"
              value={form.dtnasc || ""}
              onChange={onDtnascChange}
              placeholder="DD/MM/AAAA"
              maxLength={10}
              style={erroDtnasc ? { outline: "2px solid #dc2626" } : {}}
            />
            {erroDtnasc && <span style={{ color: "#dc2626", fontSize: 10, whiteSpace: "nowrap" }}>{erroDtnasc}</span>}
          </div>
          <div className="field campo-idade">
            <label>IDADE:</label>
            <input type="text" value={idade} readOnly tabIndex={-1} />
          </div>
        </div>

        {/* ─── Linha 5: CPF / CNS / Sexo ─── */}
        <div className="row">
          <div className="field" style={{ flex: 1.5 }}>
            <label>CPF:</label>
            <input
              ref={cpfRef}
              type="text"
              value={formatCPF(form.num_cpf)}
              onChange={onCPFChange}
              placeholder="000.000.000-00"
              maxLength={14}
              autoFocus
            />
            {erroCpf && <span style={{ color: "#dc2626", fontSize: 10, whiteSpace: "nowrap" }}>{erroCpf}</span>}
          </div>
          <div className="field" style={{ flex: 1.5 }}>
            <label>CARTÃO SUS:</label>
            <input
              type="text"
              value={formatCNS(form.cns)}
              onChange={onCNSChange}
              placeholder="000 0000 0000 0000"
              maxLength={18}
            />
            {erroCns && <span style={{ color: "#dc2626", fontSize: 10, whiteSpace: "nowrap" }}>{erroCns}</span>}
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>SEXO:</label>
            <label>
              M{" "}
              <input
                type="radio"
                name="bol-sexo"
                value="M"
                checked={form.sexo === "M"}
                onChange={() => onSexoChange("M")}
              />
            </label>
            {" "}
            <label>
              F{" "}
              <input
                type="radio"
                name="bol-sexo"
                value="F"
                checked={form.sexo === "F"}
                onChange={() => onSexoChange("F")}
              />
            </label>
          </div>
        </div>

        {/* ─── Linha 6: Estado Civil ─── */}
        <div className="row">
          <div className="field">
            <label>ESTADO CIVIL:</label>
            <div className="checkbox-group">
              {civisLegado.map((c) => (
                <label key={c}>
                  {c}{" "}
                  <input
                    type="radio"
                    name="bol-civil"
                    value={c}
                    checked={form.estado_civil === c}
                    onChange={() => onFieldChange({ target: { name: "estado_civil", value: c } })}
                  />
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* ─── Linha 7: Raça/Cor + Ocupação ─── */}
        <div className="row">
          <div className="field" style={{ flex: 2.5 }}>
            <label>RAÇA/COR:</label>
            <div className="checkbox-group">
              {racasBoletim.map((r) => (
                <label key={r.cod}>
                  {r.label}{" "}
                  <input
                    type="radio"
                    name="bol-raca"
                    value={r.cod}
                    checked={form.raca === r.cod}
                    onChange={() => onRacaChange(r.cod)}
                  />
                </label>
              ))}
            </div>
          </div>
          <div className="field" style={{ flex: 1.5 }}>
            <label>OCUPAÇÃO:</label>
            <input type="text" name="ocupacao" value={form.ocupacao || ""} onChange={onFieldChange} />
          </div>
        </div>

        {/* ─── Linha 8: Nome da Mãe ─── */}
        <div className="row">
          <div className="field">
            <label>NOME DA MÃE:</label>
            <input type="text" name="maepcn" value={form.maepcn || ""} onChange={onFieldChange} />
          </div>
        </div>

        {/* ─── Linha 9: Responsável + Tel ─── */}
        <div className="row">
          <div className="field" style={{ flex: 1 }}>
            <label>RESPONSÁVEL:</label>
            <input type="text" name="responsavel" value={form.responsavel || ""} onChange={onFieldChange} />
          </div>
          <div className="field" style={{ flex: "0 0 175px" }}>
            <label>TEL:</label>
            <input
              type="text"
              value={formatTelefone(form.telefone)}
              onChange={onTelChange}
              maxLength={15}
            />
          </div>
        </div>

        {/* ─── Linha 10: Endereço + Nº ─── */}
        <div className="row">
          <div className="field" style={{ flex: 1 }}>
            <label>ENDEREÇO:</label>
            <input type="text" name="logpcn" value={form.logpcn || ""} onChange={onFieldChange} />
            {onFamilia && (
              <button
                type="button"
                className="btn-familia no-print"
                onClick={onFamilia}
                title="Copiar endereço do último paciente registrado"
              >
                Família
              </button>
            )}
          </div>
          <div className="field campo-num">
            <label>Nº:</label>
            <input type="text" name="numpcn" value={form.numpcn || ""} onChange={onFieldChange} maxLength={20} />
          </div>
        </div>

        {/* ─── Linha 11: Bairro / Cidade / UF ─── */}
        <div className="row spacer-row">
          <div className="field" style={{ flex: 3 }}>
            <label>BAIRRO:</label>
            <input type="text" name="bairro_pcnte" value={form.bairro_pcnte || ""} onChange={onFieldChange} />
          </div>
          <div className="field" style={{ flex: 1.5 }}>
            <label>CIDADE:</label>
            <input type="text" name="cidade" value={form.cidade || ""} onChange={onFieldChange} />
          </div>
          <div className="field" style={{ flex: "0 0 58px" }}>
            <label>UF:</label>
            <input type="text" name="estado" value={form.estado || ""} maxLength={2} onChange={onFieldChange} style={{ width: 24 }} />
          </div>
        </div>

        {/* ─── CLASSIFICAÇÃO DE RISCO SSVV ─── */}
        <div className="section-title">CLASSIFICAÇÃO DE RISCO SSVV</div>
        <table className="tabela-risco">
          <tbody>
            <tr>
              <td className="color-box">VERMELHO</td>
              <td>PA: <input type="text" className="input-ssvv" /></td>
              <td>SPO²: <input type="text" className="input-ssvv" /></td>
              <td>AO: <input type="text" className="input-ssvv" /></td>
            </tr>
            <tr>
              <td className="color-box">LARANJA</td>
              <td>FC: <input type="text" className="input-ssvv" /></td>
              <td>HGT: <input type="text" className="input-ssvv" /></td>
              <td>RV: <input type="text" className="input-ssvv" /></td>
            </tr>
            <tr>
              <td className="color-box">AMARELO</td>
              <td>FR: <input type="text" className="input-ssvv" /></td>
              <td>DOR: <input type="text" className="input-ssvv" /></td>
              <td>RM: <input type="text" className="input-ssvv" /></td>
            </tr>
            <tr>
              <td className="color-box">VERDE</td>
              <td>TEMP: <input type="text" className="input-ssvv" /></td>
              <td>PESO: <input type="text" className="input-ssvv" /></td>
              <td>TOTAL: <input type="text" className="input-ssvv" /></td>
            </tr>
            <tr>
              <td className="color-box">AZUL</td>
              <td colSpan={3}></td>
            </tr>
          </tbody>
        </table>

        {/* ─── Comorbidades ─── */}
        <div className="row" style={{ borderTop: "none" }}>
          <div className="field">
            <label>COMORBIDADES:</label>
            <div className="checkbox-group">
              {comorbidades.map((c) => (
                <label key={c}>
                  {c} <input type="checkbox" />
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* ─── Medicamentos ─── */}
        <div className="row">
          <div className="field">
            <label>MEDICAMENTOS EM USO?</label>
            <label>NÃO <input type="radio" name="bol-medic" /></label>
            <label>SIM <input type="radio" name="bol-medic" /></label>
            <input type="text" style={{ marginLeft: 10 }} />
          </div>
        </div>

        {/* ─── Alergias ─── */}
        <div className="row spacer-row">
          <div className="field">
            <label>ALERGIAS?</label>
            <label>NÃO <input type="radio" name="bol-alergia" /></label>
            <label>SIM <input type="radio" name="bol-alergia" /></label>
            <input type="text" style={{ marginLeft: 10 }} />
          </div>
        </div>

        <div className="section-title">ANOTAÇÕES DA CLASSIFICAÇÃO</div>
        <div className="handwriting-area ha-anotacoes"></div>

        <div className="section-title">RESUMO DA HISTÓRIA CLÍNICA</div>
        <div className="handwriting-area ha-historia"></div>

        <div className="section-title">HIPÓTESE DIAGNÓSTICA</div>
        <div className="handwriting-area ha-hipotese"></div>
      </form>
    </div>
  );
}
