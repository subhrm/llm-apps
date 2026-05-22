# Hacker News AI Dashboard Client

An interactive, state-of-the-art Web Client for the Hacker News Summarization Agent. Built with **Vite**, **React**, **TypeScript**, and styled using premium **Vanilla CSS** aesthetics. It connects to the stateful LangGraph backend server over the Server-Sent Events (SSE) AG-UI protocol utilizing the official `@ag-ui/client` package.

---

## 🎨 Design & Aesthetic Guidelines

The dashboard is designed with **Rich Aesthetics** to provide an immersive, high-quality user experience:
* **Deep Dark Mode Theme**: Designed with an ultra-sleek, deep-space background featuring HSL radial color gradients.
* **Glassmorphism Panels**: Semi-transparent content boards using standard CSS backdrop-filters, subtle borders, and smooth shadows.
* **Neon Highlights**: Vibrant orange and purple accents that react smoothly to user interaction.
* **Micro-Animations**: Fluid transitions, hover scaling, and active tool-calling spinners that keep the interface responsive and alive.
* **Modern Typography**: Uses browser-optimized clean fonts for maximum readability.

---

## ✨ Features

* **Live Story Board**: Loads and displays Hacker News frontpage stories reactively by capturing the streaming outputs of the `list_top_stories` tool result events.
* **Agent Console**: Streams the agent's thought logs in real time. Tracks active tool execution, showing the called tool name and cumulative arguments in a glassmorphism progress badge.
* **Discussion Summary Actions**: Trigger instant comment thread summaries directly from the story card action buttons.
* **External Scraper Integration**: Initiates full main-body article scraping and summaries directly for any story linking to an external website.
* **Interactive Prompting**: Custom prompt input console at the bottom-right for full conversational agent interactions.

---

## 📂 Directory Structure

```
hn-web-app/
├── package.json         # Project manifests, scripts, and dependencies
├── vite.config.ts       # Vite bundler configurations
├── index.html           # Main entry document
└── src/
    ├── main.tsx         # React bootstrap render
    ├── App.tsx          # Dual-panel dashboard layout & @ag-ui/client agent loop hook
    ├── index.css        # Vanilla CSS premium design layout stylesheet
    ├── types/
    │   └── HNTypes.ts   # Strongly typed interfaces for stories and active tools
    └── utils/
        └── markdown.ts  # Custom lightweight markdown-to-HTML parser
```

---

## ⚙️ Installation & Development

### 1. Install Dependencies
Run the command below in the `hn-web-app` directory to set up all packages:
```bash
npm install
```

### 2. Start the Dev Server
Launch Vite's hot-reloading web development server:
```bash
npm run dev -- --host 127.0.0.1
```
The client will be active and accessible at **[http://127.0.0.1:5173/](http://127.0.0.1:5173/)**.

### 3. Production Build
To validate TypeScript compile safety and bundle the production files inside `dist/`:
```bash
npm run build
```

---

## 🔗 Connection Configuration

The web client connects to the LangGraph FastAPI backend via `@ag-ui/client`'s `HttpAgent`:
* **Capabilities check**: `GET http://127.0.0.1:8001/capabilities` on load to verify server status.
* **Chat subscriptions**: `POST http://127.0.0.1:8001/chat` to stream execution events.
