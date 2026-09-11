import React from 'react';
import { GitHubConnectorCard } from './GitHubConnectorCard';
import { FetchConnectorCard } from './FetchConnectorCard';
import { Cpu, ShieldCheck } from 'lucide-react';

export const MCPConnectorsHub: React.FC = () => {
  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '36px 20px' }}>
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 14px',
            borderRadius: '999px',
            background: 'rgba(99, 102, 241, 0.12)',
            border: '1px solid rgba(99, 102, 241, 0.25)',
            color: '#a5b4fc',
            fontSize: '0.75rem',
            fontWeight: 700,
            marginBottom: '12px',
          }}
        >
          <Cpu size={14} />
          <span>Model Context Protocol (MCP) Management</span>
        </div>
        <h1
          style={{
            fontSize: '1.85rem',
            fontWeight: 800,
            color: '#f8fafc',
            margin: '0 0 8px',
            letterSpacing: '-0.02em',
          }}
        >
          Active MCP Tool Connectors
        </h1>
        <p style={{ fontSize: '0.92rem', color: '#94a3b8', margin: 0, lineHeight: 1.5, maxWidth: '720px' }}>
          Manage dynamic external integrations used by your AI Copilot and Study Generator to inspect code repositories and read external documentation.
        </p>
      </div>

      {/* Side-by-Side Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
          gap: '28px',
          alignItems: 'stretch',
        }}
      >
        <GitHubConnectorCard />
        <FetchConnectorCard />
      </div>

      {/* Security Footer Notice */}
      <div
        style={{
          marginTop: '32px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '16px 20px',
          background: 'rgba(15, 23, 42, 0.5)',
          border: '1px solid rgba(51, 65, 85, 0.5)',
          borderRadius: '12px',
          fontSize: '0.8rem',
          color: '#94a3b8',
          lineHeight: 1.5,
        }}
      >
        <ShieldCheck size={20} color="#34d399" style={{ flexShrink: 0 }} />
        <span>
          Personal tokens are encrypted at rest with AES-Fernet encryption in MongoDB and loaded only into user-isolated Stdio subprocesses during active agent runs. Changing settings in one connector is strictly isolated and never affects other connectors.
        </span>
      </div>
    </div>
  );
};
