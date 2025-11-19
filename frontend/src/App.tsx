import { Routes, Route } from 'react-router-dom';
import ProjectList from './components/ProjectList/ProjectList';
import ProjectLandingPage from './components/ProjectSession/ProjectLandingPage';
import ChatSessionPage from './components/ProjectSession/ChatSessionPage';
import './App.css';

function App() {
  return (
    <div className="app">
      <Routes>
        <Route path="/" element={<ProjectList />} />
        <Route path="/projects/:projectId" element={<ProjectLandingPage />} />
        <Route path="/projects/:projectId/chat/:sessionId" element={<ChatSessionPage />} />
      </Routes>
    </div>
  );
}

export default App;
