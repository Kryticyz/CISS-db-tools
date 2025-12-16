import { useState, useEffect } from 'react';
import { useDeletionQueue } from '../context/DeletionQueueContext';
import type { DeletionPreview, DeletionResult } from '../types';

interface ConfirmModalProps {
  onClose: () => void;
}

function ConfirmModal({ onClose }: ConfirmModalProps) {
  const { getPreview, confirmDeletion, isLoading } = useDeletionQueue();
  const [preview, setPreview] = useState<DeletionPreview | null>(null);
  const [result, setResult] = useState<DeletionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);

  // Load preview on mount
  useEffect(() => {
    let mounted = true;
    async function loadPreview() {
      try {
        const data = await getPreview();
        if (mounted) setPreview(data);
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to load preview');
        }
      }
    }
    loadPreview();
    return () => {
      mounted = false;
    };
  }, [getPreview]);

  const handleConfirm = async () => {
    try {
      setIsConfirming(true);
      setError(null);
      const res = await confirmDeletion();
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Deletion failed');
    } finally {
      setIsConfirming(false);
    }
  };

  // Show result view
  if (result) {
    return (
      <div className="modal-backdrop" onClick={onClose}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h3 className="text-lg font-semibold">
              {result.success ? 'Deletion Complete' : 'Deletion Completed with Errors'}
            </h3>
          </div>
          <div className="modal-body">
            <div className="space-y-4">
              <div className={`p-4 rounded-lg ${result.success ? 'bg-green-50' : 'bg-yellow-50'}`}>
                <p className={result.success ? 'text-green-700' : 'text-yellow-700'}>
                  Successfully deleted <strong>{result.deleted_count}</strong> files
                </p>
                {result.failed_count > 0 && (
                  <p className="text-red-700 mt-2">
                    Failed to delete <strong>{result.failed_count}</strong> files
                  </p>
                )}
              </div>

              {result.failed_files.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Failed files:</h4>
                  <ul className="text-sm text-red-600 max-h-40 overflow-y-auto">
                    {result.failed_files.map((f, i) => (
                      <li key={i}>
                        {f.path}: {f.error}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
          <div className="modal-footer">
            <button onClick={onClose} className="btn btn-primary">
              Close
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Show preview/confirmation view
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal max-w-xl" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="text-lg font-semibold text-gray-900">
            Confirm Deletion
          </h3>
        </div>

        <div className="modal-body">
          {error && (
            <div className="bg-red-50 text-red-700 p-4 rounded-lg mb-4">
              {error}
            </div>
          )}

          {!preview ? (
            <div className="flex items-center justify-center py-8">
              <div className="spinner w-8 h-8" />
            </div>
          ) : (
            <div className="space-y-4">
              {/* Summary */}
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-800 font-medium">
                  You are about to permanently delete{' '}
                  <strong>{preview.total_files}</strong> files
                  ({preview.total_size_human})
                </p>
              </div>

              {/* Breakdown by reason */}
              <div>
                <h4 className="font-medium text-gray-900 mb-2">By reason:</h4>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(preview.by_reason).map(([reason, count]) => (
                    <span key={reason} className={`badge badge-${reason}`}>
                      {count} {reason}
                    </span>
                  ))}
                </div>
              </div>

              {/* Species affected */}
              <div>
                <h4 className="font-medium text-gray-900 mb-2">
                  Species affected ({preview.species_affected.length}):
                </h4>
                <div className="text-sm text-gray-600 max-h-24 overflow-y-auto">
                  {preview.species_affected.join(', ')}
                </div>
              </div>

              {/* Warnings */}
              {preview.warnings.length > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <h4 className="font-medium text-yellow-800 mb-2">Warnings:</h4>
                  <ul className="text-sm text-yellow-700 list-disc list-inside">
                    {preview.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Final warning */}
              <p className="text-sm text-gray-500">
                This action cannot be undone. Make sure you have a backup if needed.
              </p>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button
            onClick={onClose}
            disabled={isConfirming}
            className="btn btn-secondary"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!preview || isConfirming || isLoading}
            className="btn btn-danger"
          >
            {isConfirming ? 'Deleting...' : 'Delete Files'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmModal;
