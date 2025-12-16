import { useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { AnalysisParameters, DeletionReason } from '../types';
import { useDeletionQueue } from '../context/DeletionQueueContext';
import ParameterControls from './ParameterControls';
import DuplicatesView from './DuplicatesView';
import SimilarView from './SimilarView';
import OutliersView from './OutliersView';
import LoadingSpinner from './LoadingSpinner';
import ErrorMessage from './ErrorMessage';

type Tab = 'duplicates' | 'similar' | 'outliers';

function SpeciesReview() {
  const { species } = useParams<{ species: string }>();
  const [activeTab, setActiveTab] = useState<Tab>('duplicates');
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
