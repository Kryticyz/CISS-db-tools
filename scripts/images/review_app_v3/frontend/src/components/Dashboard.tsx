import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { SpeciesInfo } from '../types';
import LoadingSpinner from './LoadingSpinner';
import ErrorMessage from './ErrorMessage';

function Dashboard() {
  const {
    data: summary,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: api.dashboard.summary,
  });

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return <ErrorMessage message={error instanceof Error ? error.message : 'Failed to load dashboard'} />;
  }

  if (!summary) {
    return <ErrorMessage message="No data available" />;
  }

  return (
    <div className="space-y-6">
      {/* Stats overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          label="Total Species"
          value={summary.total_species}
          color="blue"
        />
        <StatCard
          label="Total Images"
          value={summary.total_images.toLocaleString()}
          color="gray"
        />
        <StatCard
          label="FAISS Status"
          value={summary.faiss_available ? 'Available' : 'Not Available'}
          color={summary.faiss_available ? 'green' : 'red'}
        />
      </div>

      {/* Species grid */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Species ({summary.species.length})
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Click a species to review duplicates, similar images, and outliers
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {summary.species.map((species) => (
            <SpeciesCard key={species.name} species={species} />
          ))}
        </div>
      </div>
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: string | number;
  color: 'blue' | 'gray' | 'green' | 'yellow' | 'red';
}

function StatCard({ label, value, color }: StatCardProps) {
  const colorClasses = {
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
    gray: 'bg-gray-50 border-gray-200 text-gray-700',
    green: 'bg-green-50 border-green-200 text-green-700',
    yellow: 'bg-yellow-50 border-yellow-200 text-yellow-700',
    red: 'bg-red-50 border-red-200 text-red-700',
  };

  return (
    <div className={`card border ${colorClasses[color]}`}>
      <div className="p-4">
        <p className="text-sm opacity-75">{label}</p>
        <p className="text-2xl font-bold">{value}</p>
      </div>
    </div>
  );
}

interface SpeciesCardProps {
  species: SpeciesInfo;
}

function SpeciesCard({ species }: SpeciesCardProps) {
  return (
    <Link
      to={`/review/${encodeURIComponent(species.name)}`}
      className={`card hover:shadow-lg transition-shadow ${
        species.processed ? 'border-green-300 bg-green-50/50' : ''
      }`}
    >
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="font-medium text-gray-900 truncate" title={species.name}>
            {species.name.replace(/_/g, ' ')}
          </h3>
          <div className="flex items-center gap-1">
            {species.processed && (
              <span
                className="bg-green-100 text-green-700 text-xs px-1.5 py-0.5 rounded"
                title="This species has been reviewed"
              >
                Done
              </span>
            )}
            {species.has_embeddings && (
              <span className="text-green-500" title="Embeddings available">
                ✓
              </span>
            )}
          </div>
        </div>

        {/* Image count */}
        <p className="text-sm text-gray-500">
          {species.image_count} images
        </p>

        {/* Embeddings status */}
        {!species.has_embeddings && (
          <p className="text-xs text-gray-400 mt-2">
            No embeddings
          </p>
        )}
      </div>
    </Link>
  );
}

export default Dashboard;
