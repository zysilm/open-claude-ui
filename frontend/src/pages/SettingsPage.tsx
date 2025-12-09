import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { settingsAPI, type ApiKeyStatus, type LLMProviderInfo } from '@/services/api';
import './SettingsPage.css';

// Placeholder patterns for API key inputs
const PROVIDER_PLACEHOLDERS: Record<string, string> = {
  openai: 'sk-...',
  anthropic: 'sk-ant-...',
  azure: 'your-azure-key',
  gemini: 'AIza...',
  mistral: 'your-mistral-key',
  groq: 'gsk_...',
  together_ai: 'your-together-key',
  cohere: 'your-cohere-key',
  deepseek: 'sk-...',
  ollama: 'not required for local',
  openrouter: 'sk-or-...',
  bedrock: 'AWS access key',
};

export default function SettingsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [editingProvider, setEditingProvider] = useState<string | null>(null);
  const [apiKeyInputs, setApiKeyInputs] = useState<Record<string, string>>({});
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { valid: boolean; message: string }>>({});
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Fetch API keys
  const { data: keysData, isLoading: isLoadingKeys } = useQuery({
    queryKey: ['apiKeys'],
    queryFn: () => settingsAPI.listApiKeys(),
  });

  // Fetch LLM providers from backend (dynamically from LiteLLM)
  const { data: providersData, isLoading: isLoadingProviders } = useQuery({
    queryKey: ['llmProviders'],
    queryFn: () => settingsAPI.getLLMProviders(true), // featured_only=true
    staleTime: 1000 * 60 * 60, // Cache for 1 hour
  });

  const providers: LLMProviderInfo[] = providersData?.providers || [];
  const isLoading = isLoadingKeys || isLoadingProviders;

  // Save API key mutation
  const saveMutation = useMutation({
    mutationFn: (data: { provider: string; api_key: string }) =>
      settingsAPI.setApiKey(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] });
      setEditingProvider(null);
      setApiKeyInputs(prev => ({ ...prev, [variables.provider]: '' }));
      setMessage({ type: 'success', text: `API key for ${variables.provider} saved successfully!` });
      setTimeout(() => setMessage(null), 5000);
    },
    onError: (error: any) => {
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to save API key' });
      setTimeout(() => setMessage(null), 5000);
    },
  });

  // Delete API key mutation
  const deleteMutation = useMutation({
    mutationFn: (provider: string) => settingsAPI.deleteApiKey(provider),
    onSuccess: (_, provider) => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] });
      setMessage({ type: 'success', text: `API key for ${provider} deleted successfully!` });
      setTimeout(() => setMessage(null), 5000);
    },
    onError: (error: any) => {
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to delete API key' });
      setTimeout(() => setMessage(null), 5000);
    },
  });

  const handleTestKey = async (provider: string) => {
    const apiKey = apiKeyInputs[provider];
    if (!apiKey) return;

    setTestingProvider(provider);
    try {
      const result = await settingsAPI.testApiKey(provider, apiKey);
      setTestResults(prev => ({ ...prev, [provider]: result }));
    } catch (error) {
      setTestResults(prev => ({
        ...prev,
        [provider]: { valid: false, message: 'Failed to test API key' },
      }));
    } finally {
      setTestingProvider(null);
    }
  };

  const handleSaveKey = (provider: string) => {
    const apiKey = apiKeyInputs[provider];
    if (!apiKey) return;
    saveMutation.mutate({ provider, api_key: apiKey });
  };

  const handleDeleteKey = (provider: string) => {
    if (confirm(`Are you sure you want to delete the API key for ${provider}?`)) {
      deleteMutation.mutate(provider);
    }
  };

  const getKeyStatus = (providerId: string): ApiKeyStatus | undefined => {
    return keysData?.api_keys.find(k => k.provider === providerId);
  };

  const isConfigured = (providerId: string) => {
    return getKeyStatus(providerId)?.is_configured || false;
  };

  const getPlaceholder = (providerId: string) => {
    return PROVIDER_PLACEHOLDERS[providerId] || 'your-api-key';
  };

  return (
    <div className="settings-page">
      <div className="settings-header">
        <button className="btn-back" onClick={() => navigate('/')}>
          ← Back to Projects
        </button>
        <h1>Settings</h1>
        <p>Manage your API keys and application settings</p>
      </div>

      <div className="settings-content">
        {message && (
          <div className={`alert alert-${message.type}`}>
            {message.text}
          </div>
        )}

        <div className="security-notice">
          <div className="security-notice-title">
            🔒 Security Notice
          </div>
          <p className="security-notice-text">
            API keys are encrypted (AES-128) before storage and never displayed after saving.
            Keys are only decrypted when making LLM API calls.
          </p>
        </div>

        <div className="settings-section">
          <h2 className="section-title">API Keys</h2>
          <p className="section-description">
            Configure API keys for LLM providers. Keys stored here take priority over environment variables.
          </p>

          {isLoading ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <div className="loading-spinner"></div>
            </div>
          ) : (
            <div className="provider-list">
              {providers.map(provider => {
                // Skip providers that don't require an API key (like ollama)
                if (provider.env_key === null) return null;

                const status = getKeyStatus(provider.id);
                const isEditing = editingProvider === provider.id;
                const configured = isConfigured(provider.id);

                return (
                  <div key={provider.id} className={`provider-card ${configured ? 'configured' : ''}`}>
                    <div className="provider-header">
                      <div className="provider-info">
                        <h3 className="provider-name">{provider.name}</h3>
                        <p className={`provider-status ${configured ? 'configured' : ''}`}>
                          {configured
                            ? `Configured (added ${new Date(status!.created_at).toLocaleDateString()})`
                            : 'Not configured'}
                        </p>
                      </div>
                      <div className="provider-actions">
                        {!isEditing && (
                          <>
                            <button
                              className="btn btn-secondary"
                              onClick={() => setEditingProvider(provider.id)}
                            >
                              {configured ? 'Update' : 'Add Key'}
                            </button>
                            {configured && (
                              <button
                                className="btn btn-danger"
                                onClick={() => handleDeleteKey(provider.id)}
                                disabled={deleteMutation.isPending}
                              >
                                Delete
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </div>

                    {isEditing && (
                      <div className="key-input-form">
                        <div className="form-group">
                          <label className="form-label">API Key</label>
                          <input
                            type="password"
                            className="form-input"
                            placeholder={getPlaceholder(provider.id)}
                            value={apiKeyInputs[provider.id] || ''}
                            onChange={(e) =>
                              setApiKeyInputs(prev => ({ ...prev, [provider.id]: e.target.value }))
                            }
                          />
                        </div>

                        {testResults[provider.id] && (
                          <div className={`alert alert-${testResults[provider.id].valid ? 'success' : 'error'}`}>
                            {testResults[provider.id].message}
                          </div>
                        )}

                        <div className="form-actions">
                          <button
                            className="btn btn-secondary"
                            onClick={() => {
                              setEditingProvider(null);
                              setApiKeyInputs(prev => ({ ...prev, [provider.id]: '' }));
                              setTestResults(prev => {
                                const newResults = { ...prev };
                                delete newResults[provider.id];
                                return newResults;
                              });
                            }}
                          >
                            Cancel
                          </button>
                          <button
                            className="btn btn-secondary"
                            onClick={() => handleTestKey(provider.id)}
                            disabled={!apiKeyInputs[provider.id] || testingProvider === provider.id}
                          >
                            {testingProvider === provider.id ? (
                              <span className="loading-spinner"></span>
                            ) : (
                              'Test Connection'
                            )}
                          </button>
                          <button
                            className="btn btn-primary"
                            onClick={() => handleSaveKey(provider.id)}
                            disabled={!apiKeyInputs[provider.id] || saveMutation.isPending}
                          >
                            {saveMutation.isPending ? (
                              <span className="loading-spinner"></span>
                            ) : (
                              'Save Key'
                            )}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
