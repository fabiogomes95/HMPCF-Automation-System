import { useState } from "react";
import Triagem from "../components/bpa/Triagem";
import Digitacao from "../components/bpa/Digitacao";
import Geracao from "../components/bpa/Geracao";
import "./Bpa.css";

const ABAS = [
  { id: "triagem", label: "🧹 Triagem", Componente: Triagem },
  { id: "digitacao", label: "✍️ Digitação", Componente: Digitacao },
  { id: "geracao", label: "📦 Geração", Componente: Geracao },
];

export default function Bpa() {
  const [aba, setAba] = useState("digitacao");
  const AbaAtiva = ABAS.find((a) => a.id === aba)?.Componente;

  return (
    <div className="bpa">
      <div className="bpa-header">
        <h1>Automação BPA</h1>
        <div className="bpa-subnav">
          {ABAS.map((a) => (
            <button
              key={a.id}
              className={`bpa-subnav-btn${aba === a.id ? " ativo" : ""}`}
              onClick={() => setAba(a.id)}
            >
              {a.label}
            </button>
          ))}
        </div>
      </div>

      {AbaAtiva && <AbaAtiva />}
    </div>
  );
}
