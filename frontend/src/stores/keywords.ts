/**
 * Keywords Store - Manages keyword research state
 */

import { create } from 'zustand';
import type { Keyword, KeywordCluster, KeywordDiscoverRequest } from '@/lib/types';
import api from '@/lib/api';

interface KeywordsState {
  keywords: Keyword[];
  clusters: KeywordCluster[];
  total: number;
  page: number;
  isLoading: boolean;
  isDiscovering: boolean;
  isClustering: boolean;
  error: string | null;
  
  // Actions
  fetchKeywords: (siteId: string, page?: number) => Promise<void>;
  fetchClusters: (siteId: string) => Promise<void>;
  discoverKeywords: (data: KeywordDiscoverRequest) => Promise<string>;
  clusterKeywords: (siteId: string) => Promise<string>;
  trackKeyword: (id: string, track: boolean) => Promise<void>;
  clearError: () => void;
}

export const useKeywordsStore = create<KeywordsState>((set, get) => ({
  keywords: [],
  clusters: [],
  total: 0,
  page: 1,
  isLoading: false,
  isDiscovering: false,
  isClustering: false,
  error: null,

  fetchKeywords: async (siteId: string, page = 1) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.getKeywords(siteId, page);
      set({
        keywords: response.items,
        total: response.total,
        page: response.page,
        isLoading: false,
      });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch keywords';
      set({ error: message, isLoading: false });
    }
  },

  fetchClusters: async (siteId: string) => {
    set({ isLoading: true, error: null });
    try {
      const clusters = await api.getClusters(siteId);
      set({ clusters, isLoading: false });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch clusters';
      set({ error: message, isLoading: false });
    }
  },

  discoverKeywords: async (data: KeywordDiscoverRequest) => {
    set({ isDiscovering: true, error: null });
    try {
      const result = await api.discoverKeywords(data);
      set({ isDiscovering: false });
      return result.task_id;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to discover keywords';
      set({ error: message, isDiscovering: false });
      throw error;
    }
  },

  clusterKeywords: async (siteId: string) => {
    set({ isClustering: true, error: null });
    try {
      const result = await api.clusterKeywords(siteId);
      set({ isClustering: false });
      return result.task_id;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to cluster keywords';
      set({ error: message, isClustering: false });
      throw error;
    }
  },

  trackKeyword: async (id: string, track: boolean) => {
    try {
      const updatedKeyword = await api.trackKeyword(id, track);
      set((state) => ({
        keywords: state.keywords.map((k) => (k.id === id ? updatedKeyword : k)),
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to update keyword';
      set({ error: message });
      throw error;
    }
  },
  
  clearError: () => set({ error: null }),
}));
