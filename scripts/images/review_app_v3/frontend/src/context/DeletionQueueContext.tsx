import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import type { QueuedFile, DeletionReason, DeletionPreview, DeletionResult } from '../types';
import { api } from '../api/client';

interface DeletionQueueContextValue {
  // State
  queue: QueuedFile[];
  isOpen: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  addToQueue: (
    files: Array<{ species: string; filename: string; size?: number }>,
    reason: DeletionReason
  ) => Promise<void>;
  removeFromQueue: (species: string, filename: string) => Promise<void>;
  clearQueue: () => Promise<void>;
  refreshQueue: () => Promise<void>;
  getPreview: () => Promise<DeletionPreview>;
  confirmDeletion: () => Promise<DeletionResult>;

  // Toggle helpers for click-to-select
  isInQueue: (species: string, filename: string) => boolean;
  toggleQueueItem: (
    species: string,
    filename: string,
    reason: DeletionReason,
    size?: number
  ) => Promise<void>;

  // UI
  toggleSidebar: () => void;
  openSidebar: () => void;
  closeSidebar: () => void;

  // Computed
  totalCount: number;
  totalSize: number;
  totalSizeHuman: string;
}

const DeletionQueueContext = createContext<DeletionQueueContextValue | null>(null);

export function useDeletionQueue() {
  const context = useContext(DeletionQueueContext);
  if (!context) {
    throw new Error('useDeletionQueue must be used within DeletionQueueProvider');
  }
  return context;
}

interface ProviderProps {
  children: ReactNode;
}

export function DeletionQueueProvider({ children }: ProviderProps) {
  const [queue, setQueue] = useState<QueuedFile[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Computed values
  const totalCount = queue.length;
  const totalSize = queue.reduce((sum, f) => sum + f.size, 0);
  const totalSizeHuman = formatSize(totalSize);

  // Refresh queue from server
  const refreshQueue = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await api.deletion.getQueue();
      setQueue(data.files);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh queue');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Add files to queue
  const addToQueue = useCallback(
    async (
      files: Array<{ species: string; filename: string; size?: number }>,
      reason: DeletionReason
    ) => {
      try {
        setIsLoading(true);
        setError(null);
        await api.deletion.addToQueue(files, reason);
        await refreshQueue();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to add to queue');
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [refreshQueue]
  );

  // Remove file from queue
  const removeFromQueue = useCallback(
    async (species: string, filename: string) => {
      try {
        setIsLoading(true);
        setError(null);
        await api.deletion.removeFromQueue(species, filename);
        await refreshQueue();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to remove from queue');
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [refreshQueue]
  );

  // Clear queue
  const clearQueue = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      await api.deletion.clearQueue();
      setQueue([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear queue');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Get preview
  const getPreview = useCallback(async () => {
    return api.deletion.preview();
  }, []);

  // Confirm deletion
  const confirmDeletion = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await api.deletion.confirm();
      // Clear local queue on success
      if (result.success) {
        setQueue([]);
      } else {
        // Refresh to get remaining failed items
        await refreshQueue();
      }
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete files');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [refreshQueue]);

  // Check if a file is in the queue
  const isInQueue = useCallback(
    (species: string, filename: string) => {
      return queue.some((f) => f.species === species && f.filename === filename);
    },
    [queue]
  );

  // Toggle a file in/out of queue (for click-to-select)
  const toggleQueueItem = useCallback(
    async (
      species: string,
      filename: string,
      reason: DeletionReason,
      size?: number
    ) => {
      if (isInQueue(species, filename)) {
        await removeFromQueue(species, filename);
      } else {
        await addToQueue([{ species, filename, size }], reason);
      }
    },
    [isInQueue, removeFromQueue, addToQueue]
  );

  // UI actions
  const toggleSidebar = useCallback(() => setIsOpen((prev) => !prev), []);
  const openSidebar = useCallback(() => setIsOpen(true), []);
  const closeSidebar = useCallback(() => setIsOpen(false), []);

  const value: DeletionQueueContextValue = {
    queue,
    isOpen,
    isLoading,
    error,
    addToQueue,
    removeFromQueue,
    clearQueue,
    refreshQueue,
    getPreview,
    confirmDeletion,
    isInQueue,
    toggleQueueItem,
    toggleSidebar,
    openSidebar,
    closeSidebar,
    totalCount,
    totalSize,
    totalSizeHuman,
  };

  return (
    <DeletionQueueContext.Provider value={value}>
      {children}
    </DeletionQueueContext.Provider>
  );
}

// Helper function
function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}
