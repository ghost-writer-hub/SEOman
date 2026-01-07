/**
 * Content Store - Manages content briefs and drafts state
 */

import { create } from 'zustand';
import type { ContentBrief, ContentDraft, BriefCreate, DraftCreate } from '@/lib/types';
import api from '@/lib/api';

interface ContentState {
  briefs: ContentBrief[];
  currentBrief: ContentBrief | null;
  drafts: ContentDraft[];
  currentDraft: ContentDraft | null;
  total: number;
  page: number;
  isLoading: boolean;
  isGenerating: boolean;
  error: string | null;
  
  // Actions
  fetchBriefs: (siteId?: string, page?: number) => Promise<void>;
  fetchBrief: (id: string) => Promise<void>;
  fetchDrafts: (briefId: string) => Promise<void>;
  fetchDraft: (id: string) => Promise<void>;
  createBrief: (data: BriefCreate) => Promise<ContentBrief>;
  generateBrief: (id: string) => Promise<ContentBrief>;
  generateDraft: (briefId: string) => Promise<ContentDraft>;
  updateDraft: (id: string, content: string) => Promise<ContentDraft>;
  setCurrentBrief: (brief: ContentBrief | null) => void;
  setCurrentDraft: (draft: ContentDraft | null) => void;
  clearError: () => void;
}

export const useContentStore = create<ContentState>((set, get) => ({
  briefs: [],
  currentBrief: null,
  drafts: [],
  currentDraft: null,
  total: 0,
  page: 1,
  isLoading: false,
  isGenerating: false,
  error: null,

  fetchBriefs: async (siteId?: string, page = 1) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.getBriefs(siteId, page);
      set({
        briefs: response.items,
        total: response.total,
        page: response.page,
        isLoading: false,
      });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch briefs';
      set({ error: message, isLoading: false });
    }
  },

  fetchBrief: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const brief = await api.getBrief(id);
      set({ currentBrief: brief, isLoading: false });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch brief';
      set({ error: message, isLoading: false });
    }
  },

  fetchDrafts: async (briefId: string) => {
    set({ isLoading: true, error: null });
    try {
      const drafts = await api.getDrafts(briefId);
      set({ drafts, isLoading: false });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch drafts';
      set({ error: message, isLoading: false });
    }
  },

  fetchDraft: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const draft = await api.getDraft(id);
      set({ currentDraft: draft, isLoading: false });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch draft';
      set({ error: message, isLoading: false });
    }
  },

  createBrief: async (data: BriefCreate) => {
    set({ isLoading: true, error: null });
    try {
      const brief = await api.createBrief(data);
      set((state) => ({
        briefs: [brief, ...state.briefs],
        total: state.total + 1,
        isLoading: false,
      }));
      return brief;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to create brief';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  generateBrief: async (id: string) => {
    set({ isGenerating: true, error: null });
    try {
      const brief = await api.generateBrief(id);
      set((state) => ({
        briefs: state.briefs.map((b) => (b.id === id ? brief : b)),
        currentBrief: state.currentBrief?.id === id ? brief : state.currentBrief,
        isGenerating: false,
      }));
      return brief;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to generate brief';
      set({ error: message, isGenerating: false });
      throw error;
    }
  },

  generateDraft: async (briefId: string) => {
    set({ isGenerating: true, error: null });
    try {
      const draft = await api.generateDraft(briefId);
      set((state) => ({
        drafts: [draft, ...state.drafts],
        isGenerating: false,
      }));
      return draft;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to generate draft';
      set({ error: message, isGenerating: false });
      throw error;
    }
  },

  updateDraft: async (id: string, content: string) => {
    set({ isLoading: true, error: null });
    try {
      const updatedDraft = await api.updateDraft(id, content);
      set((state) => ({
        drafts: state.drafts.map((d) => (d.id === id ? updatedDraft : d)),
        currentDraft: state.currentDraft?.id === id ? updatedDraft : state.currentDraft,
        isLoading: false,
      }));
      return updatedDraft;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to update draft';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  setCurrentBrief: (brief: ContentBrief | null) => set({ currentBrief: brief }),
  setCurrentDraft: (draft: ContentDraft | null) => set({ currentDraft: draft }),
  
  clearError: () => set({ error: null }),
}));
