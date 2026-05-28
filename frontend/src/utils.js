export function apenasNumeros(v) {
  return (v || "").replace(/\D/g, "");
}

export function formatCPF(v) {
  const d = apenasNumeros(v).slice(0, 11);
  if (d.length <= 3) return d;
  if (d.length <= 6) return `${d.slice(0, 3)}.${d.slice(3)}`;
  if (d.length <= 9)
    return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6)}`;
  return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`;
}

export function formatCNS(v) {
  const d = apenasNumeros(v).slice(0, 15);
  if (d.length <= 3) return d;
  if (d.length <= 7) return `${d.slice(0, 3)} ${d.slice(3)}`;
  if (d.length <= 11)
    return `${d.slice(0, 3)} ${d.slice(3, 7)} ${d.slice(7)}`;
  return `${d.slice(0, 3)} ${d.slice(3, 7)} ${d.slice(7, 11)} ${d.slice(11)}`;
}

export function formatDateBR(v) {
  const d = apenasNumeros(v).slice(0, 8);
  if (d.length <= 2) return d;
  if (d.length <= 4) return `${d.slice(0, 2)}/${d.slice(2)}`;
  return `${d.slice(0, 2)}/${d.slice(2, 4)}/${d.slice(4)}`;
}

export function parseDateToDB(v) {
  const partes = v.split("/");
  if (partes.length === 3) {
    return `${partes[2]}${partes[1]}${partes[0]}`;
  }
  return v;
}

export function parseDateFromDB(v) {
  if (!v) return "";
  const d = apenasNumeros(v);
  if (d.length === 8) return `${d.slice(6, 8)}/${d.slice(4, 6)}/${d.slice(0, 4)}`;
  return v;
}

export function formatTelefone(v) {
  const d = apenasNumeros(v).slice(0, 11);
  if (!d) return "";
  if (d.length <= 2) return `(${d}`;
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  // 10 dígitos: fixo (84) 3333-4444 — separador após 4º dígito do número
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  // 11 dígitos: celular (84) 99999-4444
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
}

export function calcularIdade(dtnasc) {
  if (!dtnasc) return null;
  const partes = dtnasc.split("/");
  if (partes.length !== 3) return null;
  const dia = parseInt(partes[0], 10);
  const mes = parseInt(partes[1], 10);
  const ano = parseInt(partes[2], 10);
  if (!dia || !mes || !ano) return null;

  const hoje = new Date();
  const nasc = new Date(ano, mes - 1, dia);

  let anos = hoje.getFullYear() - nasc.getFullYear();
  let meses = hoje.getMonth() - nasc.getMonth();
  let dias = hoje.getDate() - nasc.getDate();

  if (dias < 0) {
    meses--;
    const mesAnterior = new Date(hoje.getFullYear(), hoje.getMonth(), 0);
    dias += mesAnterior.getDate();
  }
  if (meses < 0) {
    anos--;
    meses += 12;
  }

  return { anos, meses, dias };
}

export function formatarIdade(idade) {
  if (!idade) return "";
  if (idade.anos > 0)
    return `${idade.anos} ${idade.anos === 1 ? "ANO" : "ANOS"}`;
  if (idade.meses > 0)
    return `${idade.meses} ${idade.meses === 1 ? "MÊS" : "MESES"}`;
  return `${idade.dias} ${idade.dias === 1 ? "DIA" : "DIAS"}`;
}

export function validarCPF(cpf) {
  const d = apenasNumeros(cpf);
  if (d.length !== 11) return false;
  if (/^(\d)\1{10}$/.test(d)) return false;

  let sum = 0;
  for (let i = 0; i < 9; i++) sum += parseInt(d[i], 10) * (10 - i);
  let resto = sum % 11;
  const dig1 = resto < 2 ? 0 : 11 - resto;
  if (dig1 !== parseInt(d[9], 10)) return false;

  sum = 0;
  for (let i = 0; i < 10; i++) sum += parseInt(d[i], 10) * (11 - i);
  resto = sum % 11;
  const dig2 = resto < 2 ? 0 : 11 - resto;
  if (dig2 !== parseInt(d[10], 10)) return false;

  return true;
}

export function validarCNS(cns) {
  const d = apenasNumeros(cns);
  if (d.length !== 15) return false;
  if (!["1", "2", "7", "8", "9"].includes(d[0])) return false;

  let sum = 0;
  for (let i = 0; i < 15; i++) sum += parseInt(d[i], 10) * (15 - i);
  return sum % 11 === 0;
}

export function formatRegistro(num) {
  return String(num != null ? num : 0).padStart(2, "0");
}

export function calcularTurno(hora) {
  if (!hora) return "DIURNO";
  const h = parseInt(hora.split(":")[0], 10);
  return h >= 7 && h <= 18 ? "DIURNO" : "NOTURNO";
}

export function horaAtual() {
  const agora = new Date();
  return `${String(agora.getHours()).padStart(2, "0")}:${String(agora.getMinutes()).padStart(2, "0")}`;
}

export function dataAtual() {
  const agora = new Date();
  return `${String(agora.getDate()).padStart(2, "0")}/${String(agora.getMonth() + 1).padStart(2, "0")}/${agora.getFullYear()}`;
}

export function dataOperacional(dataStr, hora) {
  if (!dataStr || !hora) return dataStr || "";
  const turno = calcularTurno(hora);
  if (turno === "DIURNO") return dataStr;
  const partes = dataStr.split("/");
  const d = new Date(
    parseInt(partes[2], 10),
    parseInt(partes[1], 10) - 1,
    parseInt(partes[0], 10)
  );
  d.setDate(d.getDate() - 1);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
}

const racasIBGE = [
  { cod: "01", label: "BRANCA" },
  { cod: "02", label: "PRETA" },
  { cod: "03", label: "PARDA" },
  { cod: "04", label: "AMARELA" },
  { cod: "05", label: "INDÍGENA" },
];

export function getRacas() {
  return racasIBGE;
}
