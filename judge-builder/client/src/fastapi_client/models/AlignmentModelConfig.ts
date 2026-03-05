/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ServingEndpointConfig } from './ServingEndpointConfig';
/**
 * Configuration for alignment model selection.
 */
export type AlignmentModelConfig = {
    /**
     * Type: "default" or "serving_endpoint"
     */
    model_type?: string;
    /**
     * Serving endpoint config when model_type="serving_endpoint"
     */
    serving_endpoint?: (ServingEndpointConfig | null);
};

