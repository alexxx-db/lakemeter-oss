import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Calculator from './pages/Calculator'
import EstimateDetail from './pages/EstimateDetail'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="calculator" element={<Calculator />} />
        <Route path="calculator/:id" element={<Calculator />} />
        <Route path="estimate/:id" element={<EstimateDetail />} />
      </Route>
    </Routes>
  )
}

export default App


