/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { JudgeCreateRequest } from '../models/JudgeCreateRequest';
import type { JudgeResponse } from '../models/JudgeResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class JudgeBuildersService {
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
}
