/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CreateLabelingSessionRequest } from '../models/CreateLabelingSessionRequest';
import type { CreateLabelingSessionResponse } from '../models/CreateLabelingSessionResponse';
import type { LabelingProgress } from '../models/LabelingProgress';
import type { TraceRequest } from '../models/TraceRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class LabelingService {
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
}
