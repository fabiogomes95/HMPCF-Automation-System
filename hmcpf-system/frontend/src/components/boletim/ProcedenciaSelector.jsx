import "./boletim.css";

const procedencias = [
  { v: "SAMU", label: "SAMU", cls: "btn-samu" },
  { v: "TROCA", label: "TROCA", cls: "btn-troca" },
  { v: "OBS", label: "UBS", cls: "btn-obs" },
  { v: "GUARDA", label: "GUARDA", cls: "btn-guarda" },
  { v: "NORMAL", label: "NORMAL", cls: "btn-normal" },
];

export default function ProcedenciaSelector({ value, onChange }) {
  return (
    <div className="procedencia-container no-print">
      <label className="procedencia-titulo">Procedência / Observação:</label>
      <div className="procedencia-botoes">
        {procedencias.map((p) => (
          <label
            key={p.v}
            className={`btn-proc ${p.cls} ${value === p.v ? "ativo" : ""}`}
          >
            <input
              type="radio"
              name="procedencia"
              value={p.v}
              checked={value === p.v}
              onChange={() => onChange(p.v)}
            />
            <strong>{p.label}</strong>
          </label>
        ))}
      </div>
    </div>
  );
}
