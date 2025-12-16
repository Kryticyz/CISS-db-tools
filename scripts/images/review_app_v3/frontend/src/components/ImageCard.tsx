import { useState } from 'react';
import { api } from '../api/client';

interface ImageCardProps {
  species: string;
  filename: string;
  size: number;
  isSelected?: boolean;
  onToggleSelect?: () => void;
}

function ImageCard({ species, filename, size, isSelected, onToggleSelect }: ImageCardProps) {
  const [hasError, setHasError] = useState(false);
  const imageUrl = api.images.url(species, filename);

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleClick = () => {
    if (onToggleSelect) {
      onToggleSelect();
    }
  };

  return (
    <div
      className={`image-card group ${onToggleSelect ? 'cursor-pointer' : ''} ${
        isSelected ? 'ring-2 ring-red-500 ring-offset-2' : ''
      }`}
      onClick={handleClick}
    >
      {hasError ? (
        <div className="w-full h-32 bg-gray-200 flex items-center justify-center">
          <span className="text-gray-400 text-xs">Failed to load</span>
        </div>
      ) : (
        <img
          src={imageUrl}
          alt={filename}
          loading="lazy"
          onError={() => setHasError(true)}
          className="w-full h-32 object-cover"
        />
      )}

      {/* Selection indicator */}
      {isSelected && (
        <div className="absolute top-2 right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
      )}

      {/* Info overlay on hover */}
      <div className="absolute inset-0 bg-black bg-opacity-60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-2">
        <p className="text-white text-xs truncate" title={filename}>
          {filename}
        </p>
        <p className="text-gray-300 text-xs">{formatSize(size)}</p>
      </div>
    </div>
  );
}

export default ImageCard;
