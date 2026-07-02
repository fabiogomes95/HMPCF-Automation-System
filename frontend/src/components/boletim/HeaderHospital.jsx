import "./boletim.css";

export default function HeaderHospital() {
  return (
    <div className="header-container">
      <div className="header-logo">
        <img src="/img/brasao-extremoz.png" alt="Brasão Extremoz" />
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
          <div className="priority-item">
            <label>Gestante <input type="checkbox" /></label>
          </div>
          <div className="priority-item">
            <label>Criança <input type="checkbox" /></label>
          </div>
          <div className="priority-item">
            <label>TEA/PCD <input type="checkbox" /></label>
          </div>
          <div className="priority-item">
            <label>Idoso <input type="checkbox" /></label>
          </div>
          <div className="priority-item">
            <label>Pequenas Cirurgias <input type="checkbox" /></label>
          </div>
          <div className="priority-item">
            <label>Outros <input type="checkbox" /></label>
          </div>
        </div>
      </div>
    </div>
  );
}
