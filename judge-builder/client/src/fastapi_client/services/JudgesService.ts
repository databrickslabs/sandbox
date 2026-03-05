/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AlignmentModelConfig } from '../models/AlignmentModelConfig';
import type { JudgeCreateRequest } from '../models/JudgeCreateRequest';
import type { JudgeResponse } from '../models/JudgeResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class JudgesService {
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
}
