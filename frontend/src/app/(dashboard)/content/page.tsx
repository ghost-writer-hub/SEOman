'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Header } from '@/components/layout/Header';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Modal } from '@/components/ui/Modal';
import { Spinner } from '@/components/ui/Spinner';
import { Alert } from '@/components/ui/Alert';
import { BriefCard } from '@/components/content/BriefCard';
import { useContentStore } from '@/stores/content';
import { useSitesStore } from '@/stores/sites';

export default function ContentPage() {
  const router = useRouter();
  const { briefs, isLoading, isGenerating, error, fetchBriefs, createBrief, generateBrief, generateDraft } = useContentStore();
  const { sites, fetchSites } = useSitesStore();
  const [selectedSite, setSelectedSite] = useState('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newKeyword, setNewKeyword] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    fetchSites();
  }, [fetchSites]);

  useEffect(() => {
    fetchBriefs(selectedSite || undefined);
  }, [fetchBriefs, selectedSite]);

  // Auto-select first site
  useEffect(() => {
    if (sites.length > 0 && !selectedSite) {
      setSelectedSite(sites[0].id);
    }
  }, [sites, selectedSite]);

  const siteOptions = sites.map(site => ({ value: site.id, label: site.name }));

  const handleCreateBrief = async () => {
    if (!newKeyword.trim() || !selectedSite) return;
    
    setIsCreating(true);
    try {
      const brief = await createBrief({
        site_id: selectedSite,
        target_keyword: newKeyword.trim(),
      });
      setIsCreateModalOpen(false);
      setNewKeyword('');
      
      // Auto-generate the brief
      await generateBrief(brief.id);
      fetchBriefs(selectedSite);
    } catch (err) {
      // Error handled by store
    } finally {
      setIsCreating(false);
    }
  };

  const handleGenerateBrief = async (id: string) => {
    await generateBrief(id);
    fetchBriefs(selectedSite);
  };

  const handleCreateDraft = async (briefId: string) => {
    try {
      const draft = await generateDraft(briefId);
      router.push(`/content/${briefId}/drafts/${draft.id}`);
    } catch (err) {
      // Error handled by store
    }
  };

  return (
    <div>
      <Header title="Content" />
      
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-4">
            <div className="w-64">
              <Select
                value={selectedSite}
                onChange={(e) => setSelectedSite(e.target.value)}
                options={siteOptions}
                placeholder="Select a site"
              />
            </div>
          </div>
          <Button onClick={() => setIsCreateModalOpen(true)} disabled={!selectedSite}>
            Create Brief
          </Button>
        </div>

        {error && (
          <Alert variant="error" className="mb-6">
            {error}
          </Alert>
        )}

        {!selectedSite ? (
          <div className="text-center py-12">
            <p className="text-gray-500">Select a site to view content briefs</p>
          </div>
        ) : isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner size="lg" />
          </div>
        ) : briefs.length === 0 ? (
          <div className="text-center py-12">
            <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No content briefs yet</h3>
            <p className="text-gray-500 mb-4">Create an AI-powered content brief to start writing</p>
            <Button onClick={() => setIsCreateModalOpen(true)}>Create Your First Brief</Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {briefs.map((brief) => (
              <BriefCard
                key={brief.id}
                brief={brief}
                onClick={() => router.push(`/content/${brief.id}`)}
                onGenerate={() => handleGenerateBrief(brief.id)}
                onCreateDraft={() => handleCreateDraft(brief.id)}
              />
            ))}
          </div>
        )}
      </div>

      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create Content Brief"
        description="Enter a target keyword to generate an AI-powered content brief"
        footer={
          <>
            <Button variant="outline" onClick={() => setIsCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateBrief} isLoading={isCreating || isGenerating}>
              Create & Generate
            </Button>
          </>
        }
      >
        <Input
          label="Target Keyword"
          value={newKeyword}
          onChange={(e) => setNewKeyword(e.target.value)}
          placeholder="e.g., best seo tools 2024"
          helperText="The primary keyword you want to rank for"
        />
      </Modal>
    </div>
  );
}
