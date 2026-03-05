/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AlignmentStartResponse } from '../models/AlignmentStartResponse';
import type { EvaluationResult } from '../models/EvaluationResult';
import type { TestJudgeRequest } from '../models/TestJudgeRequest';
import type { TestJudgeResponse } from '../models/TestJudgeResponse';
import type { TraceRequest } from '../models/TraceRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AlignmentService {
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
}
