import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { useDeletionQueue } from '../context/DeletionQueueContext';
import ImageCard from './ImageCard';
import LoadingSpinner from './LoadingSpinner';
import ErrorMessage from './ErrorMessage';

interface OutliersViewProps {
  species: string;
  thresholdPercentile: number;
  onAddToQueue: (files: Array<{ filename: string; size: number }>) => void;
}

function OutliersView({
  species,
  thresholdPercentile,
  onAddToQueue,
}: OutliersViewProps) {
  const { isInQueue, toggleQueueItem } = useDeletionQueue();
  const {
    data: result,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['outliers', species, thresholdPercentile],
    queryFn: () =>
      api.analysis.outliers(species, {
        threshold_percentile: thresholdPercentile,
      }),
  });

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return (
      <ErrorMessage
        message={error instanceof Error ? error.message : 'Failed to load outliers'}
      />
    );
  }

  if (!result || result.outliers.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No outliers found with current threshold
      </div>
    );
  }

  const handleAddAllToQueue = () => {
    const files = result.outliers.map((o) => ({
      filename: o.filename,
      size: o.size,
    }));
    onAddToQueue(files);
  };

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600">
            Found <span className="font-semibold">{result.outlier_count}</span> outliers
            (distance &gt; {result.computed_threshold.toFixed(4)})
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Species mean: {result.mean_distance.toFixed(4)} | std: {result.std_distance.toFixed(4)}
          </p>
        </div>
        {result.outliers.length > 0 && (
          <button
            onClick={handleAddAllToQueue}
            className="btn btn-primary btn-sm"
          >
            Queue All Outliers ({result.outliers.length})
          </button>
        )}
      </div>

      {/* Info box */}
      <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
        <p className="text-sm text-orange-800">
          <strong>What are outliers?</strong> These images are unusually different
          from other images of this species. They may be mislabeled, poor quality,
          or show unusual specimens. Review carefully before deleting.
        </p>
      </div>

      {/* Outlier images */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {result.outliers.map((outlier) => (
          <div key={outlier.filename} className="relative">
            <ImageCard
              species={species}
              filename={outlier.filename}
              size={outlier.size}
              isSelected={isInQueue(species, outlier.filename)}
              onToggleSelect={() =>
                toggleQueueItem(species, outlier.filename, 'outlier', outlier.size)
              }
            />
            <div className="absolute top-2 left-2">
              <span className="badge badge-outlier">Outlier</span>
            </div>
            {/* Distance info */}
            <div className="absolute bottom-0 left-0 right-0 bg-black bg-opacity-60 text-white text-xs p-1">
              <div className="flex justify-between">
                <span>dist: {outlier.distance_to_centroid.toFixed(3)}</span>
                {outlier.z_score !== undefined && (
                  <span>z: {outlier.z_score.toFixed(1)}</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default OutliersView;
