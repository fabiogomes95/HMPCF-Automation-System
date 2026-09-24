// Entrada das telas do BPA servidas pelo BPA LOCAL (http://localhost:8503/ui/),
// sem o servidor do hospital: sem login e sem o menu do sistema. O BPA local só
// escuta em 127.0.0.1, então só quem está no próprio notebook chega aqui.
// Mesmas telas da aba BPA do sistema (pages/bpa/).
import React from "react";
import ReactDOM from "react-dom/client";
import Bpa from "./pages/bpa/Bpa";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Bpa />
  </React.StrictMode>
);
