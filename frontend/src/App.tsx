import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import ChatPage from "./pages/ChatPage";
import UploadPage from "./pages/UploadPage";

export default function App() {
  return (
    <div className="app">
      <header className="topnav">
        <span className="brand">RAG Basic Implementation</span>
        <nav>
          <NavLink to="/chat">Chat</NavLink>
          <NavLink to="/upload">Upload</NavLink>
        </nav>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/upload" element={<UploadPage />} />
        </Routes>
      </main>
    </div>
  );
}
