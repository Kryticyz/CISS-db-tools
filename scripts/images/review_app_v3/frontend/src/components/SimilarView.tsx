import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { SimilarGroup } from '../types';
import { useDeletionQueue } from '../context/DeletionQueueContext';
import ImageCard from './ImageCard';
import LoadingSpinner from './LoadingSpinner';
import ErrorMessage from './ErrorMessage';

interface SimilarViewProps {
  species: string;
  similarityThreshold: number;
  onAddToQueue: (files: Array<{ filename: string; size: number }>) => void;
}

function SimilarView({
  species,
  similarityThreshold,
  onAddToQueue,
}: SimilarViewProps) {
  const {
    data: result,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['similar', species, similarityThreshold],
    queryFn: () =>
      api.analysis.similar(species, {
        similarity_threshold: similarityThreshold,
      }),
  });

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return (
      <ErrorMessage
        message={error instanceof Error ? error.message : 'Failed to load similar images'}
      />
    );
  }

  if (!result || result.similar_groups.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No similar image groups found with current threshold
      </div>
    );
  }

  // Filter out groups with >100 images (too large to display)
  const MAX_GROUP_SIZE = 100;
  const filteredGroups = result.similar_groups.filter(g => g.count <= MAX_GROUP_SIZE);
  const skippedCount = result.similar_groups.length - filteredGroups.length;

  // For similar images, we keep the first (largest) and queue the rest
  const handleAddGroupToQueue = (group: SimilarGroup) => {
    // Skip the first image (keep it), queue the rest
    const files = group.images.slice(1).map((img) => ({
      filename: img.filename,
      size: img.size,
    }));
    onAddToQueue(files);
  };

  const handleAddAllToQueue = () => {
    const allFiles = filteredGroups.flatMap((group) =>
      group.images.slice(1).map((img) => ({
        filename: img.filename,
        size: img.size,
      }))
    );
    onAddToQueue(allFiles);
  };

  const totalToDelete = filteredGroups.reduce(
    (sum, g) => sum + g.images.length - 1,
    0
  );

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600">
            Found <span className="font-semibold">{filteredGroups.length}</span> groups
            of similar images
            {result.from_faiss && (
              <span className="text-green-600 ml-2">(using FAISS)</span>
            )}
          </p>
          {skippedCount > 0 && (
            <p className="text-xs text-gray-400 mt-1">
              {skippedCount} group{skippedCount > 1 ? 's' : ''} with &gt;{MAX_GROUP_SIZE} images hidden
            </p>
          )}
        </div>
        {totalToDelete > 0 && (
          <button
            onClick={handleAddAllToQueue}
            className="btn btn-primary btn-sm"
          >
            Queue All Similar ({totalToDelete})
          </button>
        )}
      </div>

      {/* Similar groups */}
      <div className="space-y-6">
        {filteredGroups.map((group) => (
          <SimilarGroupCard
            key={group.group_id}
            group={group}
            species={species}
            onAddToQueue={() => handleAddGroupToQueue(group)}
          />
        ))}
      </div>
    </div>
  );
}

interface SimilarGroupCardProps {
  group: SimilarGroup;
  species: string;
  onAddToQueue: () => void;
}

function SimilarGroupCard({ group, species, onAddToQueue }: SimilarGroupCardProps) {
  const { isInQueue, toggleQueueItem } = useDeletionQueue();
  const toDelete = group.images.length - 1;

  return (
    <div className="border border-gray-200 rounded-lg p-4">
      {/* Group header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-gray-900">
          Group {group.group_id}
          <span className="text-gray-500 font-normal ml-2">
            ({group.count} similar images)
          </span>
        </h3>
        {toDelete > 0 && (
          <button onClick={onAddToQueue} className="btn btn-danger btn-sm">
            Queue {toDelete} for Deletion
          </button>
        )}
      </div>

      {/* Images */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {group.images.map((img, index) => (
          <div key={img.filename} className="relative">
            <ImageCard
              species={species}
              filename={img.filename}
              size={img.size}
              isSelected={isInQueue(species, img.filename)}
              onToggleSelect={() =>
                toggleQueueItem(species, img.filename, 'similar', img.size)
              }
            />
            <div className="absolute top-2 left-2">
              {index === 0 ? (
                <span className="badge badge-clean">Keep</span>
              ) : (
                <span className="badge badge-similar">Similar</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default SimilarView;
