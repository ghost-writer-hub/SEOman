/**
 * Audits Store - Manages SEO audit state
 */

import { create } from 'zustand';
import type { AuditRun, SeoIssue, AuditCreate } from '@/lib/types';
import api from '@/lib/api';

interface AuditsState {
  audits: AuditRun[];
  currentAudit: AuditRun | null;
  issues: SeoIssue[];
  total: number;
  page: number;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  fetchAudits: (siteId?: string, page?: number) => Promise<void>;
  fetchAudit: (id: string) => Promise<void>;
  fetchIssues: (auditId: string) => Promise<void>;
  createAudit: (data: AuditCreate) => Promise<AuditRun>;
  markIssueFixed: (issueId: string) => Promise<void>;
  setCurrentAudit: (audit: AuditRun | null) => void;
  clearError: () => void;
}

export const useAuditsStore = create<AuditsState>((set, get) => ({
  audits: [],
  currentAudit: null,
  issues: [],
  total: 0,
  page: 1,
  isLoading: false,
  error: null,

  fetchAudits: async (siteId?: string, page = 1) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.getAudits(siteId, page);
      set({
        audits: response.items,
        total: response.total,
        page: response.page,
        isLoading: false,
      });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch audits';
      set({ error: message, isLoading: false });
    }
  },

  fetchAudit: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const audit = await api.getAudit(id);
      set({ currentAudit: audit, isLoading: false });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch audit';
      set({ error: message, isLoading: false });
    }
  },

  fetchIssues: async (auditId: string) => {
    set({ isLoading: true, error: null });
    try {
      const issues = await api.getAuditIssues(auditId);
      set({ issues, isLoading: false });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch issues';
      set({ error: message, isLoading: false });
    }
  },

  createAudit: async (data: AuditCreate) => {
    set({ isLoading: true, error: null });
    try {
      const audit = await api.createAudit(data);
      set((state) => ({
        audits: [audit, ...state.audits],
        total: state.total + 1,
        isLoading: false,
      }));
      return audit;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to create audit';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  markIssueFixed: async (issueId: string) => {
    try {
      const updatedIssue = await api.markIssueFixed(issueId);
      set((state) => ({
        issues: state.issues.map((i) => (i.id === issueId ? updatedIssue : i)),
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to mark issue as fixed';
      set({ error: message });
      throw error;
    }
  },

  setCurrentAudit: (audit: AuditRun | null) => set({ currentAudit: audit }),
  
  clearError: () => set({ error: null }),
}));
