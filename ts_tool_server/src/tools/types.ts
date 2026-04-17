/**
 * Type definitions for the Tool Server.
 */

export interface ToolCallRequest {
  arguments: Record<string, unknown>;
  sandbox_config?: SandboxConfig;
}

export interface ToolCallResponse {
  success: boolean;
  result?: unknown;
  error?: string;
}

export interface ToolDefinition {
  name: string;
  description: string;
  input_schema: ToolInputSchema;
}

export interface ToolInputSchema {
  type: 'object';
  properties: Record<string, ToolProperty>;
  required?: string[];
}

export interface ToolProperty {
  type: string;
  description?: string;
}

export interface SandboxConfig {
  network?: {
    allowedDomains?: string[];
    deniedDomains?: string[];
    allowUnixSockets?: boolean;
    allowAllUnixSockets?: boolean;
    allowLocalBinding?: boolean;
    httpProxyPort?: number;
    socksProxyPort?: number;
  };
  filesystem?: {
    denyRead?: string[];
    allowRead?: string[];
    allowWrite?: string[];
    denyWrite?: string[];
  };
  ignoreViolations?: boolean;
  enableWeakerNestedSandbox?: boolean;
  enableWeakerNetworkIsolation?: boolean;
}
