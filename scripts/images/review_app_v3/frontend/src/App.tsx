import { Routes, Route, Navigate } from 'react-router-dom';
import { DeletionQueueProvider } from './context/DeletionQueueContext';
import Dashboard from './components/Dashboard';
import SpeciesReview from './components/SpeciesReview';
import DeletionQueueSidebar from './components/DeletionQueueSidebar';

function App() {
  return (
    <DeletionQueueProvider>
      <div className="min-h-screen bg-gray-100">
        {/* Header */}
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <h1 className="text-xl font-semibold text-gray-900">
              PlantNet Image Review
            </h1>
          </div>
        </header>

        {/* Main content */}
        <main className="max-w-7xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/review/:species" element={<SpeciesReview />} />
          </Routes>
        </main>

        {/* Floating deletion queue sidebar */}
        <DeletionQueueSidebar />
      </div>
    </DeletionQueueProvider>
  );
}

export default App;
