# RagStudio · Frontend

Aplicação desktop do RagStudio: Electron + Vite + React 19 + TypeScript + Tailwind 4 + shadcn/ui.
A interface não acessa o banco: toda operação é uma chamada à CLI Python (`python -m ragstudio ...`) feita pelo
processo principal do Electron.

```bash
npm install          # dependências (o postinstall confere o binário do Electron)
npm run dev          # app com hot reload; `-- --remoteDebuggingPort 9222` expõe o CDP
npm run start        # build de produção + app
npm run check        # typecheck (node + web) + eslint
npm run build        # electron-vite build
npm run format       # prettier
```

Normalmente não é preciso entrar aqui: `../run.sh` faz as verificações e abre o app.

```
src/main/        processo principal: python.ts (interpretador, spawn, streaming) · ipc.ts · protocolo ragstudio://
src/preload/     contextBridge → window.api {run, stream, cancelStream, onProgress, diálogos, shell, getPaths}
src/renderer/src/
  lib/           api.ts (cliente tipado da CLI) · types.ts (formas do JSON) · routes.ts · i18n.ts · format.ts
  hooks/         use-stream (job com progresso) · use-stream-done · use-t · use-theme
  components/    ui/ (shadcn) · shared/ (tabela, métricas, barras, estados) · layout e providers
  pages/         corpus · questions · techniques · experiments · analysis · reports · settings
  locales/       textos globais (navegação, títulos, status) em pt-BR e en
```

Cada página tem o seu `i18n.ts` com as mesmas chaves em `pt-BR` e `en`, conferidas pelo TypeScript.
