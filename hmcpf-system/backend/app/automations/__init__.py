"""
automations/ — Módulos de automação do sistema.

AQUI FICAM:
  As automações que atualmente estão em automacao/ no sistema legado.
  Exemplos: RPA de digitação, limpeza de dados, processamento em lote.

PADRÃO: TEMPLATE METHOD
  Cada automação herda de BaseAutomation e implementa o método execute().
  Isso garante que todas sigam o mesmo contrato.

  Uso futuro:
    automacao = DigitacaoRPA()
    resultado = await automacao.execute()
    # resultado → {"status": "ok", "processados": 150, "erros": 2}

ARQUIVOS:
  base.py → Classe abstrata BaseAutomation (contrato)
  (futuro: digitacao_rpa.py, limpador.py, sincronizador.py, etc.)
"""
