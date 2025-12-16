import { useState } from 'react';
import { api } from '../api/client';

interface ImageCardProps {
  species: string;
  filename: string;
  size: number;
}

function ImageCard({ species, filename, size }: ImageCardProps) {
  const [hasError, setHasError] = useState(false);
  const imageUrl = api.images.url(species, filename);

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="image-card group">
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
