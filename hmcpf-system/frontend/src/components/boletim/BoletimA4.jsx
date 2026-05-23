import HeaderHospital from "./HeaderHospital";
import "./boletim.css";

/* ─── helpers ─── */
const racasLegado = [
  "BRANCA", "PRETA", "PARDA", "AMARELA", "INDÍGENA",
];

const civisLegado = [
  "SOLTEIRO", "CASADO", "UNIÃO ESTÁVEL", "DIVORCIADO", "VIÚVO",
];

const comorbidades = [
  "HAS", "DM", "DISLIPIDEMIA", "ETILISTA", "TABAGISTA", "OUTROS",
];

export default function BoletimA4({
  paciente = {},
  idade = "",
  atdInfo = {},
  onDataChange,
  onHoraChange,
  onRegistroChange,
}) {
  const p = paciente;

  return (
    <div className="page">
      <form id="formBoletim">
        <HeaderHospital />

        {/* ─── Linha 1: Data / Hora / Registro ─── */}
        <div className="row top-border spacer-row">
          <div className="field">
            <label>DATA DE ATENDIMENTO:</label>
            <input type="text" value={atdInfo.data || ""} onChange={onDataChange} />
          </div>
          <div className="field">
            <label>HORA:</label>
            <input type="text" value={atdInfo.hora || ""} onChange={onHoraChange} />
          </div>
          <div className="field">
            <label>REGISTRO:</label>
            <input type="text" value={atdInfo.registro || ""} onChange={onRegistroChange} />
          </div>
        </div>

        {/* ─── Linha 2: Nome completo ─── */}
        <div className="row top-border">
          <div className="field">
            <label>NOME COMPLETO:</label>
            <input type="text" value={p.nome || ""} readOnly />
          </div>
        </div>

        {/* ─── Linha 3: Nome Social ─── */}
        <div className="row">
          <div className="field">
            <label>NOME SOCIAL:</label>
            <input type="text" value={p.nome_social || ""} readOnly />
          </div>
        </div>

        {/* ─── Linha 4: Naturalidade / DN / Idade ─── */}
        <div className="row">
          <div className="field" style={{ flex: 2 }}>
            <label>NATURALIDADE:</label>
            <input type="text" value={p.naturalidade || ""} readOnly />
          </div>
          <div className="field" style={{ flex: 1.2 }}>
            <label>DN:</label>
            <input type="text" value={p.dtnasc || ""} readOnly />
          </div>
          <div className="field" style={{ flex: 0.8 }}>
            <label>IDADE:</label>
            <input type="text" value={idade} readOnly />
          </div>
        </div>

        {/* ─── Linha 5: CPF / CNS / Sexo ─── */}
        <div className="row">
          <div className="field" style={{ flex: 1.5 }}>
            <label>CPF:</label>
            <input type="text" value={p.num_cpf || ""} readOnly />
          </div>
          <div className="field" style={{ flex: 1.5 }}>
            <label>CARTÃO SUS:</label>
            <input type="text" value={p.cns || ""} readOnly />
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>SEXO:</label>
            <label> M <input type="radio" name="bol-sexo" value="M" checked={p.sexoNome === "MASCULINO"} readOnly /> </label>
            <label> F <input type="radio" name="bol-sexo" value="F" checked={p.sexoNome === "FEMININO"} readOnly /> </label>
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
                    checked={p.estadoCivil === c}
                    readOnly
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
              {racasLegado.map((r) => (
                <label key={r}>
                  {r}{" "}
                  <input
                    type="radio"
                    name="bol-raca"
                    value={r}
                    checked={p.racaNome === r}
                    readOnly
                  />
                </label>
              ))}
            </div>
          </div>
          <div className="field" style={{ flex: 1.5 }}>
            <label>OCUPAÇÃO:</label>
            <input type="text" value={p.ocupacao || ""} readOnly />
          </div>
        </div>

        {/* ─── Linha 8: Nome da Mãe ─── */}
        <div className="row">
          <div className="field">
            <label>NOME DA MÃE:</label>
            <input type="text" value={p.maepcn || ""} readOnly />
          </div>
        </div>

        {/* ─── Linha 9: Responsável + Tel ─── */}
        <div className="row">
          <div className="field" style={{ flex: 2.5 }}>
            <label>RESPONSÁVEL:</label>
            <input type="text" value={p.responsavel || ""} readOnly />
          </div>
          <div className="field" style={{ flex: 1.5 }}>
            <label>TEL:</label>
            <input type="text" value={p.telefone || ""} readOnly />
          </div>
        </div>

        {/* ─── Linha 10: Endereço + Nº ─── */}
        <div className="row">
          <div className="field" style={{ flex: 3.2 }}>
            <label>ENDEREÇO:</label>
            <input type="text" value={p.logpcn || ""} readOnly />
          </div>
          <div className="field" style={{ flex: 0.8 }}>
            <label>Nº:</label>
            <input type="text" value={p.numpcn || ""} readOnly />
          </div>
        </div>

        {/* ─── Linha 11: Bairro / Cidade / UF ─── */}
        <div className="row spacer-row">
          <div className="field" style={{ flex: 1.5 }}>
            <label>BAIRRO:</label>
            <input type="text" value={p.bairro_pcnte || ""} readOnly />
          </div>
          <div className="field" style={{ flex: 1.5 }}>
            <label>CIDADE:</label>
            <input type="text" value={p.cidade || ""} readOnly />
          </div>
          <div className="field" style={{ flex: 0.5 }}>
            <label>UF:</label>
            <input type="text" value={p.estado || ""} maxLength={2} readOnly />
          </div>
        </div>

        {/* ─── CLASSIFICAÇÃO DE RISCO SSVV ─── */}
        <div className="section-title">CLASSIFICAÇÃO DE RISCO SSVV</div>
        <table className="tabela-risco">
          <tbody>
            <tr>
              <td className="color-box" style={{ color: "#fff", background: "#dc3545" }}>VERMELHO</td>
              <td>PA: <input type="text" className="input-ssvv" /></td>
              <td>SPO²: <input type="text" className="input-ssvv" /></td>
              <td>AO: <input type="text" className="input-ssvv" /></td>
            </tr>
            <tr>
              <td className="color-box" style={{ color: "#fff", background: "#fd7e14" }}>LARANJA</td>
              <td>FC: <input type="text" className="input-ssvv" /></td>
              <td>HGT: <input type="text" className="input-ssvv" /></td>
              <td>RV: <input type="text" className="input-ssvv" /></td>
            </tr>
            <tr>
              <td className="color-box" style={{ color: "#000", background: "#ffc107" }}>AMARELO</td>
              <td>FR: <input type="text" className="input-ssvv" /></td>
              <td>DOR: <input type="text" className="input-ssvv" /></td>
              <td>RM: <input type="text" className="input-ssvv" /></td>
            </tr>
            <tr>
              <td className="color-box" style={{ color: "#fff", background: "#28a745" }}>VERDE</td>
              <td>TEMP: <input type="text" className="input-ssvv" /></td>
              <td>PESO: <input type="text" className="input-ssvv" /></td>
              <td>TOTAL: <input type="text" className="input-ssvv" /></td>
            </tr>
            <tr>
              <td className="color-box" style={{ color: "#fff", background: "#007bff" }}>AZUL</td>
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

        {/* ─── Anotações da Classificação ─── */}
        <div className="section-title">ANOTAÇÕES DA CLASSIFICAÇÃO</div>
        <div className="handwriting-area" style={{ height: 75 }}></div>

        {/* ─── Resumo da História Clínica ─── */}
        <div className="section-title">RESUMO DA HISTÓRIA CLÍNICA</div>
        <div className="handwriting-area" style={{ height: 125 }}></div>

        {/* ─── Hipótese Diagnóstica ─── */}
        <div className="section-title">HIPÓTESE DIAGNÓSTICA</div>
        <div className="handwriting-area" style={{ height: 125 }}></div>
      </form>
    </div>
  );
}
