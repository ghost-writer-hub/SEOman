/**
 * Plans Store - Manages SEO plans and tasks state
 */

import { create } from 'zustand';
import type { SeoPlan, SeoTask, PlanCreate, TaskCreate } from '@/lib/types';
import api from '@/lib/api';

interface PlansState {
  plans: SeoPlan[];
  currentPlan: SeoPlan | null;
  tasks: SeoTask[];
  total: number;
  page: number;
  isLoading: boolean;
  isGenerating: boolean;
  error: string | null;
  
  // Actions
  fetchPlans: (siteId?: string, page?: number) => Promise<void>;
  fetchPlan: (id: string) => Promise<void>;
  fetchTasks: (planId: string) => Promise<void>;
  createPlan: (data: PlanCreate) => Promise<SeoPlan>;
  generatePlan: (siteId: string) => Promise<SeoPlan>;
  updatePlan: (id: string, data: Partial<PlanCreate>) => Promise<SeoPlan>;
  deletePlan: (id: string) => Promise<void>;
  createTask: (planId: string, data: TaskCreate) => Promise<SeoTask>;
  updateTask: (taskId: string, data: Partial<TaskCreate & { status: string }>) => Promise<SeoTask>;
  setCurrentPlan: (plan: SeoPlan | null) => void;
  clearError: () => void;
}

export const usePlansStore = create<PlansState>((set, get) => ({
  plans: [],
  currentPlan: null,
  tasks: [],
  total: 0,
  page: 1,
  isLoading: false,
  isGenerating: false,
  error: null,

  fetchPlans: async (siteId?: string, page = 1) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.getPlans(siteId, page);
      set({
        plans: response.items,
        total: response.total,
        page: response.page,
        isLoading: false,
      });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch plans';
      set({ error: message, isLoading: false });
    }
  },

  fetchPlan: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const plan = await api.getPlan(id);
      set({ currentPlan: plan, isLoading: false });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch plan';
      set({ error: message, isLoading: false });
    }
  },

  fetchTasks: async (planId: string) => {
    set({ isLoading: true, error: null });
    try {
      const tasks = await api.getTasks(planId);
      set({ tasks, isLoading: false });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch tasks';
      set({ error: message, isLoading: false });
    }
  },

  createPlan: async (data: PlanCreate) => {
    set({ isLoading: true, error: null });
    try {
      const plan = await api.createPlan(data);
      set((state) => ({
        plans: [plan, ...state.plans],
        total: state.total + 1,
        isLoading: false,
      }));
      return plan;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to create plan';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  generatePlan: async (siteId: string) => {
    set({ isGenerating: true, error: null });
    try {
      const plan = await api.generatePlan(siteId);
      set((state) => ({
        plans: [plan, ...state.plans],
        total: state.total + 1,
        isGenerating: false,
      }));
      return plan;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to generate plan';
      set({ error: message, isGenerating: false });
      throw error;
    }
  },

  updatePlan: async (id: string, data: Partial<PlanCreate>) => {
    set({ isLoading: true, error: null });
    try {
      const updatedPlan = await api.updatePlan(id, data);
      set((state) => ({
        plans: state.plans.map((p) => (p.id === id ? updatedPlan : p)),
        currentPlan: state.currentPlan?.id === id ? updatedPlan : state.currentPlan,
        isLoading: false,
      }));
      return updatedPlan;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to update plan';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  deletePlan: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      await api.deletePlan(id);
      set((state) => ({
        plans: state.plans.filter((p) => p.id !== id),
        total: state.total - 1,
        currentPlan: state.currentPlan?.id === id ? null : state.currentPlan,
        isLoading: false,
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to delete plan';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  createTask: async (planId: string, data: TaskCreate) => {
    set({ isLoading: true, error: null });
    try {
      const task = await api.createTask(planId, data);
      set((state) => ({
        tasks: [...state.tasks, task],
        isLoading: false,
      }));
      return task;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to create task';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  updateTask: async (taskId: string, data: Partial<TaskCreate & { status: string }>) => {
    try {
      const updatedTask = await api.updateTask(taskId, data);
      set((state) => ({
        tasks: state.tasks.map((t) => (t.id === taskId ? updatedTask : t)),
      }));
      return updatedTask;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to update task';
      set({ error: message });
      throw error;
    }
  },

  setCurrentPlan: (plan: SeoPlan | null) => set({ currentPlan: plan }),
  
  clearError: () => set({ error: null }),
}));
