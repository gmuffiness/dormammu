import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import SimulationViewer from './components/SimulationViewer'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/simulation/:id" element={<SimulationViewer />} />
      </Routes>
    </BrowserRouter>
  )
}
