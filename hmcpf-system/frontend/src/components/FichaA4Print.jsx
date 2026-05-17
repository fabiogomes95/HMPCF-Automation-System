import "./FichaA4Print.css";

export default function FichaA4Print({ paciente, onChange }) {
  const p = paciente || {};

  const change = (name, value) => {
    if (onChange) onChange({ target: { name, value } });
  };

  return (
    <div className="page" id="fichaA4Print">
      <form id="formBoletimPrint">
        { /* ── CABEÇALHO ──────────────────────────────── */ }
        <div className="header-container">
          <div className="header-logo">
            <img src="/logo.png" alt="Logo" />
          </div>
          <div className="header-text">
            PREFEITURA MUNICIPAL DE EXTREMOZ <br />
            SECRETARIA MUNICIPAL DE SAÚDE <br />
            HOSPITAL M. PRES. CAFÉ FILHO <br />
            <strong> BOLETIM DE ATENDIMENTO </strong>
          </div>
          <div className="header-priority">
            <strong>PRIORIDADE:</strong>
            <div className="priority-grid">
              <div className="priority-item"> Gestante <input type="checkbox" /></div>
              <div className="priority-item"> Criança <input type="checkbox" /></div>
              <div className="priority-item"> TEA/PCD <input type="checkbox" /></div>
              <div className="priority-item"> Idoso <input type="checkbox" /></div>
              <div className="priority-item"> Outros <input type="checkbox" /></div>
            </div>
          </div>
        </div>

        { /* ── DATA / HORA / REGISTRO ─────────────────── */ }
        <div className="row top-border spacer-row">
          <div className="field">
            <label> DATA DE ATENDIMENTO: </label>
            <input type="text" name="data" value={p.data || new Date().toLocaleDateString("pt-BR")} readOnly />
          </div>
          <div className="field">
            <label> HORA:</label>
            <input type="text" name="hora" value={p.hora || new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })} readOnly />
          </div>
          <div className="field">
            <label> REGISTRO: </label>
            <input type="text" name="registro" value={p.registro || ""} onChange={(e) => change("registro", e.target.value)} />
          </div>
        </div>

        { /* ── NOME COMPLETO ──────────────────────────── */ }
        <div className="row top-border">
          <div className="field" style={{ display: "flex", alignItems: "center" }}>
            <label> NOME COMPLETO: </label>
            <input type="text" name="nome" value={(p.nome || "").toUpperCase()} onChange={(e) => change("nome", e.target.value)} />
          </div>
        </div>

        { /* ── NOME SOCIAL ────────────────────────────── */ }
        <div className="row">
          <div className="field">
            <label> NOME SOCIAL: </label>
            <input type="text" name="nomeSocial" value={(p.nomeSocial || "").toUpperCase()} onChange={(e) => change("nomeSocial", e.target.value)} />
          </div>
        </div>

        { /* ── NATURALIDADE / DN / IDADE ──────────────── */ }
        <div className="row">
          <div className="field" style={{ flex: 2 }}>
            <label> NATURALIDADE: </label>
            <input type="text" name="naturalidade" value={(p.naturalidade || "").toUpperCase()} onChange={(e) => change("naturalidade", e.target.value)} />
          </div>
          <div className="field" style={{ flex: 1.2 }}>
            <label> DN: </label>
            <input type="text" name="dn" value={p.dn || ""} onChange={(e) => change("dn", e.target.value)} maxLength={10} />
          </div>
          <div className="field" style={{ flex: 0.8 }}>
            <label> IDADE: </label>
            <input type="text" name="idade" value={p.idade || ""} onChange={(e) => change("idade", e.target.value)} />
          </div>
        </div>

        { /* ── CPF / SUS / SEXO ───────────────────────── */ }
        <div className="row">
          <div className="field" style={{ flex: 1.5 }}>
            <label> CPF: </label>
            <input type="text" name="cpf" value={p.cpf || ""} onChange={(e) => change("cpf", e.target.value)} maxLength={14} />
          </div>
          <div className="field" style={{ flex: 1.5 }}>
            <label> CARTÃO SUS: </label>
            <input type="text" name="sus" value={p.sus || ""} onChange={(e) => change("sus", e.target.value)} maxLength={19} />
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label> SEXO: </label>
            <label> M <input type="radio" name="sexo" value="M" checked={p.sexo === "M"} onChange={(e) => change("sexo", e.target.value)} /> </label>
            <label> F <input type="radio" name="sexo" value="F" checked={p.sexo === "F"} onChange={(e) => change("sexo", e.target.value)} /> </label>
          </div>
        </div>

        { /* ── ESTADO CIVIL ───────────────────────────── */ }
        <div className="row">
          <div className="field">
            <label>ESTADO CIVIL:</label>
            <div className="checkbox-group">
              {["SOLTEIRO", "CASADO", "UNIÃO ESTÁVEL", "DIVORCIADO", "VIÚVO"].map((op) => (
                <label key={op}>
                  {op} <input type="radio" name="civil" value={op} checked={p.civil?.toUpperCase() === op} onChange={(e) => change("civil", e.target.value)} />
                </label>
              ))}
            </div>
          </div>
        </div>

        { /* ── RAÇA/COR / OCUPAÇÃO ────────────────────── */ }
        <div className="row">
          <div className="field" style={{ flex: 2.5 }}>
            <label> RAÇA/COR: </label>
            <div className="checkbox-group">
              {["BRANCA", "PRETA", "PARDA", "AMARELA", "INDÍGENA"].map((op) => (
                <label key={op}>
                  {op} <input type="radio" name="raca" value={op} checked={p.raca?.toUpperCase() === op} onChange={(e) => change("raca", e.target.value)} />
                </label>
              ))}
            </div>
          </div>
          <div className="field" style={{ flex: 1.5 }}>
            <label> OCUPAÇÃO: </label>
            <input type="text" name="ocupacao" value={(p.ocupacao || "").toUpperCase()} onChange={(e) => change("ocupacao", e.target.value)} />
          </div>
        </div>

        { /* ── NOME DA MÃE ────────────────────────────── */ }
        <div className="row">
          <div className="field">
            <label> NOME DA MÃE: </label>
            <input type="text" name="mae" value={(p.mae || "").toUpperCase()} onChange={(e) => change("mae", e.target.value)} />
          </div>
        </div>

        { /* ── RESPONSÁVEL / TELEFONE ─────────────────── */ }
        <div className="row">
          <div className="field" style={{ flex: 2.5 }}>
            <label> RESPONSÁVEL: </label>
            <input type="text" name="responsavel" value={(p.responsavel || "").toUpperCase()} onChange={(e) => change("responsavel", e.target.value)} />
          </div>
          <div className="field" style={{ flex: 1.5 }}>
            <label> TEL: </label>
            <input type="text" name="tel" value={p.tel || ""} onChange={(e) => change("tel", e.target.value)} />
          </div>
        </div>

        { /* ── ENDEREÇO / Nº ──────────────────────────── */ }
        <div className="row">
          <div className="field" style={{ flex: 3.2 }}>
            <label> ENDEREÇO: </label>
            <input type="text" name="endereco" value={(p.endereco || "").toUpperCase()} onChange={(e) => change("endereco", e.target.value)} />
          </div>
          <div className="field" style={{ flex: 0.8 }}>
            <label> Nº: </label>
            <input type="text" name="numero" value={p.numero || ""} onChange={(e) => change("numero", e.target.value)} />
          </div>
        </div>

        { /* ── BAIRRO / CIDADE / UF ───────────────────── */ }
        <div className="row spacer-row">
          <div className="field" style={{ flex: 1.5 }}>
            <label> BAIRRO: </label>
            <input type="text" name="bairro" value={(p.bairro || "").toUpperCase()} onChange={(e) => change("bairro", e.target.value)} />
          </div>
          <div className="field" style={{ flex: 1.5 }}>
            <label> CIDADE: </label>
            <input type="text" name="cidade" value={(p.cidade || "EXTREMOZ").toUpperCase()} onChange={(e) => change("cidade", e.target.value)} />
          </div>
          <div className="field" style={{ flex: 0.5 }}>
            <label> UF: </label>
            <input type="text" name="estado" value={(p.estado || "RN").toUpperCase()} onChange={(e) => change("estado", e.target.value)} maxLength={2} />
          </div>
        </div>

        { /* ── CLASSIFICAÇÃO DE RISCO SSVV ────────────── */ }
        <div className="section-title">CLASSIFICAÇÃO DE RISCO SSVV</div>
        <table className="tabela-risco">
          <tbody>
            <tr>
              <td className="color-box">VERMELHO</td>
              <td>PA:</td>
              <td>SPO²:</td>
              <td>AO:</td>
            </tr>
            <tr>
              <td className="color-box">LARANJA</td>
              <td>FC:</td>
              <td>HGT:</td>
              <td>RV:</td>
            </tr>
            <tr>
              <td className="color-box">AMARELO</td>
              <td>FR:</td>
              <td>DOR:</td>
              <td>RM:</td>
            </tr>
            <tr>
              <td className="color-box">VERDE</td>
              <td>TEMP:</td>
              <td>PESO:</td>
              <td>TOTAL:</td>
            </tr>
            <tr>
              <td className="color-box">AZUL</td>
              <td colSpan="3"></td>
            </tr>
          </tbody>
        </table>

        { /* ── COMORBIDADES ───────────────────────────── */ }
        <div className="row" style={{ borderTop: "none" }}>
          <div className="field">
            <label>COMORBIDADES:</label>
            <div className="checkbox-group">
              {["HAS", "DM", "DISLIPIDEMIA", "ETILISTA", "TABAGISTA", "OUTROS"].map((op) => (
                <label key={op}>
                  {op} <input type="checkbox" />
                </label>
              ))}
            </div>
          </div>
        </div>

        { /* ── MEDICAMENTOS / ALERGIAS ─────────────────── */ }
        <div className="row">
          <div className="field">
            <label>MEDICAMENTOS EM USO?</label>
            <label>NÃO <input type="radio" name="medicamentoPrint" /></label>
            <label>SIM <input type="radio" name="medicamentoPrint" /></label>
          </div>
        </div>
        <div className="row spacer-row">
          <div className="field">
            <label>ALERGIAS?</label>
            <label>NÃO <input type="radio" name="alergiaPrint" /></label>
            <label>SIM <input type="radio" name="alergiaPrint" /></label>
          </div>
        </div>

        { /* ── ÁREAS DE ESCRITA MANUAL ─────────────────── */ }
        <div className="section-title">ANOTAÇÕES DA CLASSIFICAÇÃO</div>
        <div className="handwriting-area" style={{ height: "75px" }}></div>

        <div className="section-title">RESUMO DA HISTÓRIA CLÍNICA</div>
        <div className="handwriting-area" style={{ height: "125px" }}></div>

        <div className="section-title">HIPÓTESE DIAGNÓSTICA</div>
        <div className="handwriting-area" style={{ height: "125px", borderBottom: "1px solid #000" }}></div>

      </form>
    </div>
  );
}
