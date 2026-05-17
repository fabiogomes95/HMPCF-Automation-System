/*
 * USETHEME.JS — Hook personalizado para acessar o tema.
 *
 * POR QUE UM HOOK PERSONALIZADO?
 *   Em vez de todo componente fazer:
 *     import { useContext } from "react";
 *     import { ThemeContext } from "../contexts/ThemeContext";
 *     const theme = useContext(ThemeContext);
 *
 *   Chamamos apenas:
 *     import { useTheme } from "../hooks/useTheme";
 *     const { theme, toggleTheme } = useTheme();
 *
 *   Vantagens:
 *   1. Código mais limpo e reutilizável
 *   2. Se a implementação mudar, muda só aqui
 *   3. Podemos adicionar validação (ex: erro se usar fora do provider)
 *
 * COMO USAR:
 *   function Sidebar() {
 *     const { theme, toggleTheme } = useTheme();
 *     return (
 *       <button onClick={toggleTheme}>
 *         {theme === "light" ? "🌙" : "☀️"}
 *       </button>
 *     );
 *   }
 */
import { useContext } from "react";
import { ThemeContext } from "../contexts/ThemeContext";

export function useTheme() {
  // useContext = "conecta" este componente ao ThemeContext
  // Retorna o value passado pelo ThemeProvider
  const context = useContext(ThemeContext);

  // Segurança: se alguém usar useTheme fora do ThemeProvider
  if (!context) {
    throw new Error(
      "useTheme deve ser usado dentro de um ThemeProvider. " +
        "Verifique se App.jsx está envolvendo a árvore com <ThemeProvider>."
    );
  }

  return context;
}
