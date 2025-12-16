import { useState, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type { AnalysisParameters, DeletionReason } from '../types';
import { useDeletionQueue } from '../context/DeletionQueueContext';
import ParameterControls from './ParameterControls';
import DuplicatesView from './DuplicatesView';
import SimilarView from './SimilarView';
import OutliersView from './OutliersView';
import ErrorMessage from './ErrorMessage';

type Tab = 'duplicates' | 'similar' | 'outliers';

function SpeciesReview() {
  const { species } = useParams<{ species: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<Tab>('duplicates');
  const [showMarkCompleteModal, setShowMarkCompleteModal] = useState(false);
  const [isMarkingComplete, setIsMarkingComplete] = useState(false);
  const [params, setParams] = useState<AnalysisParameters>({
    hash_size: 16,
    hamming_threshold: 5,
    similarity_threshold: 0.85,
    threshold_percentile: 95,
  });

  const { addToQueue } = useDeletionQueue();

  // Fetch parameter info for tooltips
  const { data: paramInfo } = useQuery({
    queryKey: ['parameters'],
    queryFn: api.analysis.parameters,
    staleTime: Infinity, // Parameters don't change
  });

  // Handler for parameter changes
  const handleParamChange = useCallback(
    (key: keyof AnalysisParameters, value: number) => {
      setParams((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  // Handler for adding items to deletion queue
  const handleAddToQueue = useCallback(
    async (
      files: Array<{ filename: string; size: number }>,
      reason: DeletionReason
    ) => {
      if (!species) return;
      const filesWithSpecies = files.map((f) => ({
        species,
        filename: f.filename,
        size: f.size,
      }));
      await addToQueue(filesWithSpecies, reason);
    },
    [species, addToQueue]
  );

  // Handler for marking species as complete
  const handleMarkComplete = useCallback(async () => {
    if (!species) return;
    setIsMarkingComplete(true);
    try {
      await api.deletion.markComplete(decodeURIComponent(species));
      // Invalidate dashboard query to refresh processed status
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      setShowMarkCompleteModal(false);
      // Navigate back to dashboard
      navigate('/dashboard');
    } catch (error) {
      console.error('Failed to mark species as complete:', error);
    } finally {
      setIsMarkingComplete(false);
    }
  }, [species, queryClient, navigate]);

  if (!species) {
    return <ErrorMessage message="No species specified" />;
  }

  const decodedSpecies = decodeURIComponent(species);

  return (
    <div className="space-y-6">
      {/* Header with back link */}
      <div className="flex items-center justify-between">
        <div>
          <Link
            to="/dashboard"
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            &larr; Back to Dashboard
          </Link>
          <h1 className="text-2xl font-semibold text-gray-900 mt-1">
            {decodedSpecies.replace(/_/g, ' ')}
          </h1>
        </div>
        <button
          onClick={() => setShowMarkCompleteModal(true)}
          className="btn bg-green-600 hover:bg-green-700 text-white"
        >
          Mark as Complete
        </button>
      </div>

      {/* Parameter controls */}
      <div className="card">
        <div className="card-header">
          <h2 className="font-medium text-gray-900">Analysis Parameters</h2>
        </div>
        <div className="card-body">
          <ParameterControls
            params={params}
            paramInfo={paramInfo?.parameters || []}
            onChange={handleParamChange}
            activeTab={activeTab}
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs">
        <TabButton
          active={activeTab === 'duplicates'}
          onClick={() => setActiveTab('duplicates')}
        >
          Duplicates
        </TabButton>
        <TabButton
          active={activeTab === 'similar'}
          onClick={() => setActiveTab('similar')}
        >
          Similar
        </TabButton>
        <TabButton
          active={activeTab === 'outliers'}
          onClick={() => setActiveTab('outliers')}
        >
          Outliers
        </TabButton>
      </div>

      {/* Tab content */}
      <div className="card">
        <div className="card-body">
          {activeTab === 'duplicates' && (
            <DuplicatesView
              species={decodedSpecies}
              hashSize={params.hash_size}
              hammingThreshold={params.hamming_threshold}
              onAddToQueue={(files) => handleAddToQueue(files, 'duplicate')}
            />
          )}
          {activeTab === 'similar' && (
            <SimilarView
              species={decodedSpecies}
              similarityThreshold={params.similarity_threshold}
              onAddToQueue={(files) => handleAddToQueue(files, 'similar')}
            />
          )}
          {activeTab === 'outliers' && (
            <OutliersView
              species={decodedSpecies}
              thresholdPercentile={params.threshold_percentile}
              onAddToQueue={(files) => handleAddToQueue(files, 'outlier')}
            />
          )}
        </div>
      </div>

      {/* Mark Complete Confirmation Modal */}
      {showMarkCompleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Mark Species as Complete?
              </h3>
              <p className="text-gray-600 mb-4">
                This will mark <strong>{decodedSpecies.replace(/_/g, ' ')}</strong> as
                reviewed with no deletions needed. You can still review it again later.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setShowMarkCompleteModal(false)}
                  className="btn bg-gray-100 hover:bg-gray-200 text-gray-700"
                  disabled={isMarkingComplete}
                >
                  Cancel
                </button>
                <button
                  onClick={handleMarkComplete}
                  className="btn bg-green-600 hover:bg-green-700 text-white"
                  disabled={isMarkingComplete}
                >
                  {isMarkingComplete ? 'Marking...' : 'Confirm'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

function TabButton({ active, onClick, children }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`tab ${active ? 'tab-active' : 'tab-inactive'}`}
    >
      {children}
    </button>
  );
}

export default SpeciesReview;
