import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import UploadPage from './pages/UploadPage';
import ChatPage from './pages/ChatPage';
import ThemeToggle from './components/ThemeToggle';

function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        <nav style={{ padding: '1rem 2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)' }}>
          <Link to="/" style={{ fontWeight: 600, fontSize: '1.25rem', color: 'var(--text-primary)' }}>
            Arabic Menu Extractor
          </Link>
          <ThemeToggle />
        </nav>
        
        <main className="main-content">
          <Routes>
            <Route path="/" element={<UploadPage />} />
            <Route path="/chat/:menuId" element={<ChatPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
