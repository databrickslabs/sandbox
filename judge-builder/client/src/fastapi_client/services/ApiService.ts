/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AlignmentModelConfig } from '../models/AlignmentModelConfig';
import type { AlignmentStartResponse } from '../models/AlignmentStartResponse';
import type { CreateLabelingSessionRequest } from '../models/CreateLabelingSessionRequest';
import type { CreateLabelingSessionResponse } from '../models/CreateLabelingSessionResponse';
import type { EvaluationResult } from '../models/EvaluationResult';
import type { JudgeCreateRequest } from '../models/JudgeCreateRequest';
import type { JudgeResponse } from '../models/JudgeResponse';
import type { LabelingProgress } from '../models/LabelingProgress';
import type { TestJudgeRequest } from '../models/TestJudgeRequest';
import type { TestJudgeResponse } from '../models/TestJudgeResponse';
import type { TraceRequest } from '../models/TraceRequest';
import type { UserInfo } from '../models/UserInfo';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ApiService {
    /**
     * List Judge Builders
     * List all judge builders.
     * @returns JudgeResponse Successful Response
     * @throws ApiError
     */
    public static listJudgeBuildersApiJudgeBuildersGet(): CancelablePromise<Array<JudgeResponse>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/judge-builders/',
        });
    }
    /**
     * Create Judge Builder
     * Create a new judge builder.
     * @param requestBody
     * @returns JudgeResponse Successful Response
     * @throws ApiError
     */
    public static createJudgeBuilderApiJudgeBuildersPost(
        requestBody: JudgeCreateRequest,
    ): CancelablePromise<JudgeResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/judge-builders/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Judge Builder
     * Get a judge builder by ID.
     * @param judgeId
     * @returns JudgeResponse Successful Response
     * @throws ApiError
     */
    public static getJudgeBuilderApiJudgeBuildersJudgeIdGet(
        judgeId: string,
    ): CancelablePromise<JudgeResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/judge-builders/{judge_id}',
            path: {
                'judge_id': judgeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Judge Builder
     * Delete a judge builder.
     * @param judgeId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteJudgeBuilderApiJudgeBuildersJudgeIdDelete(
        judgeId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/judge-builders/{judge_id}',
            path: {
                'judge_id': judgeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Judges
     * List all judges.
     * @returns JudgeResponse Successful Response
     * @throws ApiError
     */
    public static listJudgesApiJudgesGet(): CancelablePromise<Array<JudgeResponse>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/judges/',
        });
    }
    /**
     * Create Judge
     * Create a new judge (direct judge creation, not full orchestration).
     * @param requestBody
     * @returns JudgeResponse Successful Response
     * @throws ApiError
     */
    public static createJudgeApiJudgesPost(
        requestBody: JudgeCreateRequest,
    ): CancelablePromise<JudgeResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/judges/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Judge
     * Get a judge by ID.
     * @param judgeId
     * @returns JudgeResponse Successful Response
     * @throws ApiError
     */
    public static getJudgeApiJudgesJudgeIdGet(
        judgeId: string,
    ): CancelablePromise<JudgeResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/judges/{judge_id}',
            path: {
                'judge_id': judgeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Judge
     * Delete a judge.
     * @param judgeId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteJudgeApiJudgesJudgeIdDelete(
        judgeId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/judges/{judge_id}',
            path: {
                'judge_id': judgeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Alignment Model
     * Update the alignment model configuration for a judge.
     * @param judgeId
     * @param requestBody
     * @returns JudgeResponse Successful Response
     * @throws ApiError
     */
    public static updateAlignmentModelApiJudgesJudgeIdAlignmentModelPatch(
        judgeId: string,
        requestBody?: (AlignmentModelConfig | null),
    ): CancelablePromise<JudgeResponse> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/judges/{judge_id}/alignment-model',
            path: {
                'judge_id': judgeId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Add Examples
     * Add examples to a judge.
     * @param judgeId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static addExamplesApiLabelingJudgeIdExamplesPost(
        judgeId: string,
        requestBody: TraceRequest,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/labeling/{judge_id}/examples',
            path: {
                'judge_id': judgeId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Examples
     * Get examples for a judge.
     * @param judgeId
     * @param includeJudgeResults
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getExamplesApiLabelingJudgeIdExamplesGet(
        judgeId: string,
        includeJudgeResults: boolean = false,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/labeling/{judge_id}/examples',
            path: {
                'judge_id': judgeId,
            },
            query: {
                'include_judge_results': includeJudgeResults,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Labeling Progress
     * Get labeling progress for a judge.
     * @param judgeId
     * @returns LabelingProgress Successful Response
     * @throws ApiError
     */
    public static getLabelingProgressApiLabelingJudgeIdLabelingProgressGet(
        judgeId: string,
    ): CancelablePromise<LabelingProgress> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/labeling/{judge_id}/labeling-progress',
            path: {
                'judge_id': judgeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Labeling Session
     * Create a new labeling session for a judge.
     * @param judgeId
     * @param requestBody
     * @returns CreateLabelingSessionResponse Successful Response
     * @throws ApiError
     */
    public static createLabelingSessionApiLabelingJudgeIdLabelingPost(
        judgeId: string,
        requestBody: CreateLabelingSessionRequest,
    ): CancelablePromise<CreateLabelingSessionResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/labeling/{judge_id}/labeling',
            path: {
                'judge_id': judgeId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Labeling Session
     * Get the labeling session for a judge.
     * @param judgeId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getLabelingSessionApiLabelingJudgeIdLabelingGet(
        judgeId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/labeling/{judge_id}/labeling',
            path: {
                'judge_id': judgeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Labeling Session
     * Delete the labeling session for a judge.
     * @param judgeId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteLabelingSessionApiLabelingJudgeIdLabelingDelete(
        judgeId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/labeling/{judge_id}/labeling',
            path: {
                'judge_id': judgeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Run Alignment
     * Run alignment for a judge in the background.
     * @param judgeId
     * @returns AlignmentStartResponse Successful Response
     * @throws ApiError
     */
    public static runAlignmentApiAlignmentJudgeIdAlignPost(
        judgeId: string,
    ): CancelablePromise<AlignmentStartResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/alignment/{judge_id}/align',
            path: {
                'judge_id': judgeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Alignment Status
     * Get the status of a background alignment task.
     * @param judgeId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getAlignmentStatusApiAlignmentJudgeIdAlignStatusGet(
        judgeId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/alignment/{judge_id}/align-status',
            path: {
                'judge_id': judgeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Evaluate Judge
     * Run judge evaluation on traces and log to MLflow.
     * @param judgeId
     * @param requestBody
     * @returns EvaluationResult Successful Response
     * @throws ApiError
     */
    public static evaluateJudgeApiAlignmentJudgeIdEvaluatePost(
        judgeId: string,
        requestBody: TraceRequest,
    ): CancelablePromise<EvaluationResult> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/alignment/{judge_id}/evaluate',
            path: {
                'judge_id': judgeId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Test Judge
     * Test judge on a single trace (for play buttons).
     * @param judgeId
     * @param requestBody
     * @returns TestJudgeResponse Successful Response
     * @throws ApiError
     */
    public static testJudgeApiAlignmentJudgeIdTestPost(
        judgeId: string,
        requestBody: TestJudgeRequest,
    ): CancelablePromise<TestJudgeResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/alignment/{judge_id}/test',
            path: {
                'judge_id': judgeId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Alignment Comparison
     * Get alignment comparison data including metrics and confusion matrix.
     * @param judgeId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getAlignmentComparisonApiAlignmentJudgeIdAlignmentComparisonGet(
        judgeId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/alignment/{judge_id}/alignment-comparison',
            path: {
                'judge_id': judgeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Current User
     * Get current user information.
     * @returns UserInfo Successful Response
     * @throws ApiError
     */
    public static getCurrentUserApiUsersMeGet(): CancelablePromise<UserInfo> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/users/me',
        });
    }
    /**
     * List Experiments
     * List available MLflow experiments.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listExperimentsApiExperimentsGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/experiments/',
        });
    }
    /**
     * Get Experiment
     * Get experiment by ID.
     * @param experimentId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getExperimentApiExperimentsExperimentIdGet(
        experimentId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/experiments/{experiment_id}',
            path: {
                'experiment_id': experimentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Experiment Traces
     * Get traces from experiment.
     * @param experimentId
     * @param runId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getExperimentTracesApiExperimentsExperimentIdTracesGet(
        experimentId: string,
        runId?: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/experiments/{experiment_id}/traces',
            path: {
                'experiment_id': experimentId,
            },
            query: {
                'run_id': runId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Clear Caches
     * Clear all caches.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static clearCachesApiCacheClearPost(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/cache/clear',
        });
    }
    /**
     * List Serving Endpoints
     * List all serving endpoints in the workspace.
     * @param forceRefresh
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listServingEndpointsApiServingEndpointsGet(
        forceRefresh: boolean = false,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/serving-endpoints/',
            query: {
                'force_refresh': forceRefresh,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Serving Endpoint
     * Get details for a specific serving endpoint.
     * @param endpointName
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getServingEndpointApiServingEndpointsEndpointNameGet(
        endpointName: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/serving-endpoints/{endpoint_name}',
            path: {
                'endpoint_name': endpointName,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Validate Endpoint
     * Validate that an endpoint exists.
     * @param endpointName
     * @returns any Successful Response
     * @throws ApiError
     */
    public static validateEndpointApiServingEndpointsEndpointNameValidatePost(
        endpointName: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/serving-endpoints/{endpoint_name}/validate',
            path: {
                'endpoint_name': endpointName,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
