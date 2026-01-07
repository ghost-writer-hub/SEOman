/**
 * Sites Store - Manages sites state
 */

import { create } from 'zustand';
import type { Site, SiteCreate, SiteUpdate } from '@/lib/types';
import api from '@/lib/api';

interface SitesState {
  sites: Site[];
  currentSite: Site | null;
  total: number;
  page: number;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  fetchSites: (page?: number) => Promise<void>;
  fetchSite: (id: string) => Promise<void>;
  createSite: (data: SiteCreate) => Promise<Site>;
  updateSite: (id: string, data: SiteUpdate) => Promise<Site>;
  deleteSite: (id: string) => Promise<void>;
  setCurrentSite: (site: Site | null) => void;
  clearError: () => void;
}

export const useSitesStore = create<SitesState>((set, get) => ({
  sites: [],
  currentSite: null,
  total: 0,
  page: 1,
  isLoading: false,
  error: null,

  fetchSites: async (page = 1) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.getSites(page);
      set({
        sites: response.items,
        total: response.total,
        page: response.page,
        isLoading: false,
      });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch sites';
      set({ error: message, isLoading: false });
    }
  },

  fetchSite: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const site = await api.getSite(id);
      set({ currentSite: site, isLoading: false });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch site';
      set({ error: message, isLoading: false });
    }
  },

  createSite: async (data: SiteCreate) => {
    set({ isLoading: true, error: null });
    try {
      const site = await api.createSite(data);
      set((state) => ({
        sites: [site, ...state.sites],
        total: state.total + 1,
        isLoading: false,
      }));
      return site;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to create site';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  updateSite: async (id: string, data: SiteUpdate) => {
    set({ isLoading: true, error: null });
    try {
      const updatedSite = await api.updateSite(id, data);
      set((state) => ({
        sites: state.sites.map((s) => (s.id === id ? updatedSite : s)),
        currentSite: state.currentSite?.id === id ? updatedSite : state.currentSite,
        isLoading: false,
      }));
      return updatedSite;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to update site';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  deleteSite: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      await api.deleteSite(id);
      set((state) => ({
        sites: state.sites.filter((s) => s.id !== id),
        total: state.total - 1,
        currentSite: state.currentSite?.id === id ? null : state.currentSite,
        isLoading: false,
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to delete site';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  setCurrentSite: (site: Site | null) => set({ currentSite: site }),
  
  clearError: () => set({ error: null }),
}));
