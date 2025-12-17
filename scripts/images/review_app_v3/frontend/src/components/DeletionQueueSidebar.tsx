import { useState } from 'react';
import { useDeletionQueue } from '../context/DeletionQueueContext';
import ConfirmModal from './ConfirmModal';
import { api } from '../api/client';

function DeletionQueueSidebar() {
  const {
    queue,
    isOpen,
    isLoading,
    error,
    totalCount,
    totalSizeHuman,
    removeFromQueue,
    clearQueue,
    toggleSidebar,
    closeSidebar,
  } = useDeletionQueue();

  const [showConfirm, setShowConfirm] = useState(false);

  // Group queue by reason for display
  const byReason = queue.reduce(
    (acc, file) => {
      acc[file.reason] = (acc[file.reason] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <>
      {/* Floating toggle button */}
      <button
        onClick={toggleSidebar}
        className={`fixed bottom-4 right-4 z-40 w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-colors ${
          totalCount > 0
            ? 'bg-red-600 hover:bg-red-700 text-white'
            : 'bg-gray-600 hover:bg-gray-700 text-white'
        }`}
      >
        <span className="text-xl">🗑️</span>
        {totalCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-white text-red-600 text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center border-2 border-red-600">
            {totalCount > 99 ? '99+' : totalCount}
          </span>
        )}
      </button>

      {/* Sidebar */}
      <div
        className={`fixed top-0 right-0 h-full w-80 bg-white shadow-xl z-50 transform transition-transform ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900">Deletion Queue</h2>
          <button
            onClick={closeSidebar}
            className="text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        </div>

        {/* Summary */}
        <div className="p-4 bg-gray-50 border-b border-gray-200">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Total files:</span>
            <span className="font-medium">{totalCount}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Total size:</span>
            <span className="font-medium">{totalSizeHuman}</span>
          </div>
          {/* Breakdown by reason */}
          {Object.entries(byReason).length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {byReason.duplicate && (
                <span className="badge badge-duplicate">{byReason.duplicate} dup</span>
              )}
              {byReason.similar && (
                <span className="badge badge-similar">{byReason.similar} sim</span>
              )}
              {byReason.outlier && (
                <span className="badge badge-outlier">{byReason.outlier} out</span>
              )}
            </div>
          )}
        </div>

        {/* Error message */}
        {error && (
          <div className="p-4 bg-red-50 text-red-700 text-sm border-b border-red-200">
            {error}
          </div>
        )}

        {/* File list */}
        <div className="flex-1 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 280px)' }}>
          {queue.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No files queued for deletion
            </div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {queue.map((file) => (
                <li
                  key={file.path}
                  className="p-3 flex items-start gap-3 hover:bg-gray-50"
                >
                  {/* Thumbnail */}
                  <img
                    src={api.images.url(file.species, file.filename)}
                    alt={file.filename}
                    className="w-12 h-12 object-cover rounded"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-900 truncate">{file.filename}</p>
                    <p className="text-xs text-gray-500">{file.species}</p>
                    <span className={`badge badge-${file.reason} mt-1`}>
                      {file.reason}
                    </span>
                  </div>
                  {/* Remove button */}
                  <button
                    onClick={() => removeFromQueue(file.species, file.filename)}
                    className="text-gray-400 hover:text-red-600"
                    disabled={isLoading}
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Actions */}
        <div className="p-4 border-t border-gray-200 space-y-2">
          <button
            onClick={clearQueue}
            disabled={isLoading || totalCount === 0}
            className="btn btn-secondary w-full"
          >
            Clear Queue
          </button>
          <button
            onClick={() => setShowConfirm(true)}
            disabled={isLoading || totalCount === 0}
            className="btn btn-danger w-full"
          >
            {isLoading ? 'Processing...' : `Review & Delete (${totalCount})`}
          </button>
        </div>
      </div>

      {/* Backdrop when sidebar is open */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-25 z-40"
          onClick={closeSidebar}
        />
      )}

      {/* Confirm modal */}
      {showConfirm && (
        <ConfirmModal onClose={() => setShowConfirm(false)} />
      )}
    </>
  );
}

export default DeletionQueueSidebar;
