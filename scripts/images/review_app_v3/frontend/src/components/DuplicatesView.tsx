import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { DuplicateGroup } from '../types';
import { useDeletionQueue } from '../context/DeletionQueueContext';
import ImageCard from './ImageCard';
import LoadingSpinner from './LoadingSpinner';
import ErrorMessage from './ErrorMessage';

interface DuplicatesViewProps {
  species: string;
  hashSize: number;
  hammingThreshold: number;
  onAddToQueue: (files: Array<{ filename: string; size: number }>) => void;
}

function DuplicatesView({
  species,
  hashSize,
  hammingThreshold,
  onAddToQueue,
}: DuplicatesViewProps) {
  const {
    data: result,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['duplicates', species, hashSize, hammingThreshold],
    queryFn: () =>
      api.analysis.duplicates(species, {
        hash_size: hashSize,
        hamming_threshold: hammingThreshold,
      }),
  });

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return (
      <ErrorMessage
        message={error instanceof Error ? error.message : 'Failed to load duplicates'}
      />
    );
  }

  if (!result || result.duplicate_groups.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No duplicates found with current parameters
      </div>
    );
  }

  const handleAddGroupToQueue = (group: DuplicateGroup) => {
    const files = group.duplicates.map((img) => ({
      filename: img.filename,
      size: img.size,
    }));
    onAddToQueue(files);
  };

  const handleAddAllToQueue = () => {
    const allFiles = result.duplicate_groups.flatMap((group) =>
      group.duplicates.map((img) => ({
        filename: img.filename,
        size: img.size,
      }))
    );
    onAddToQueue(allFiles);
  };

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600">
            Found <span className="font-semibold">{result.total_duplicates}</span> duplicates
            in <span className="font-semibold">{result.duplicate_groups.length}</span> groups
          </p>
        </div>
        {result.total_duplicates > 0 && (
          <button
            onClick={handleAddAllToQueue}
            className="btn btn-primary btn-sm"
          >
            Queue All Duplicates ({result.total_duplicates})
          </button>
        )}
      </div>

      {/* Duplicate groups */}
      <div className="space-y-6">
        {result.duplicate_groups.map((group) => (
          <DuplicateGroupCard
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

interface DuplicateGroupCardProps {
  group: DuplicateGroup;
  species: string;
  onAddToQueue: () => void;
}

function DuplicateGroupCard({ group, species, onAddToQueue }: DuplicateGroupCardProps) {
  const { isInQueue, toggleQueueItem } = useDeletionQueue();

  return (
    <div className="border border-gray-200 rounded-lg p-4">
      {/* Group header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-gray-900">
          Group {group.group_id}
          <span className="text-gray-500 font-normal ml-2">
            ({group.total_in_group} images)
          </span>
        </h3>
        <button onClick={onAddToQueue} className="btn btn-danger btn-sm">
          Queue {group.duplicates.length} for Deletion
        </button>
      </div>

      {/* Images */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {/* Keep image - also clickable for toggle */}
        <div className="relative">
          <ImageCard
            species={species}
            filename={group.keep.filename}
            size={group.keep.size}
            isSelected={isInQueue(species, group.keep.filename)}
            onToggleSelect={() =>
              toggleQueueItem(species, group.keep.filename, 'duplicate', group.keep.size)
            }
          />
          <div className="absolute top-2 left-2">
            <span className="badge badge-clean">Keep</span>
          </div>
        </div>

        {/* Duplicate images */}
        {group.duplicates.map((img) => (
          <div key={img.filename} className="relative">
            <ImageCard
              species={species}
              filename={img.filename}
              size={img.size}
              isSelected={isInQueue(species, img.filename)}
              onToggleSelect={() =>
                toggleQueueItem(species, img.filename, 'duplicate', img.size)
              }
            />
            <div className="absolute top-2 left-2">
              <span className="badge badge-duplicate">Duplicate</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default DuplicatesView;
