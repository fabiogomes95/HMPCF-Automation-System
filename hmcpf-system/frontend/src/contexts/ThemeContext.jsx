/*
 * THEMECONTEXT.JSX — Contexto de tema (dark/light mode).
 *
 * CONCEITO: React Context
 *   Context é uma forma de compartilhar dados entre componentes
 *   SEM precisar passar por props em cada nível da árvore.
 *
 *   SEM Context (ruim):
 *     <App>
 *       <Layout theme={theme}>
 *         <Sidebar theme={theme}>
 *           <Button theme={theme} />  ← prop passada por 3 níveis
 *
 *   COM Context (bom):
 *     <ThemeProvider>
 *       <Layout>
 *         <Sidebar>
 *           <Button />  ← useTheme() direto no Button
 *
 * COMO FUNCIONA:
 *   ThemeProvider = componente que envolve a app e "fornece" o tema
 *   useTheme() = hook que qualquer componente filho pode chamar
 *     para ler o tema atual ou alternar entre claro/escuro
 *
 *   O tema é salvo no localStorage para persistir entre sessões.
 *
 * ESTRUTURA:
 *   createContext → cria o "espaço" do contexto
 *   ThemeProvider → componente provedor (com useState + lógica)
 *   ThemeContext  → exportado para o hook useTheme consumir
 */
import { createContext, useCallback, useEffect, useState } from "react";

// Cria o contexto com um valor inicial vazio
// (será preenchido pelo ThemeProvider)
export const ThemeContext = createContext();

export function ThemeProvider({ children }) {
  // Estado do tema: "light" ou "dark"
  // Inicializa com o valor salvo no localStorage, ou "light" como padrão
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("hmcpf-theme") || "light";
  });

  // Efeito: sempre que o tema mudar, atualiza:
  // 1. Atributo data-theme no HTML (para o CSS aplicar)
  // 2. localStorage (para salvar a preferência)
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("hmcpf-theme", theme);
  }, [theme]);

  // Função para alternar entre claro/escuro
  // useCallback = memoiza a função (não recria a cada render)
  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  }, []);

  // O objeto passado no value é o que os consumidores recebem
  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
