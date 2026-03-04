import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface TaxFilingRequest {
  npwp: string;
  filingType: string;
  taxPeriod: string;
  taxYear: number;
  grossIncome: number;
  taxableIncome: number;
  taxDue: number;
  taxPaid: number;
  taxOverpaid: number;
  taxUnderpaid: number;
  isAmendment: boolean;
  amendmentNumber: number;
}

export interface TaxFilingResponse {
  filingId: string;
  npwp: string;
  filingType: string;
  taxPeriod: string;
  taxYear: number;
  grossIncome: number;
  taxableIncome: number;
  taxDue: number;
  taxPaid: number;
  taxOverpaid: number;
  taxUnderpaid: number;
  status: string;
  submittedDate: string;
  receiptNumber: string;
  isAmendment: boolean;
  amendmentNumber: number;
}

@Injectable({
  providedIn: 'root'
})
export class FilingService {
  private readonly apiUrl = `${environment.apiBaseUrl}/api/v1/filing`;

  private httpOptions = {
    headers: new HttpHeaders({
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    })
  };

  constructor(private http: HttpClient) {}

  /**
   * Submit a tax filing (SPT) to the CoreTax system.
   * POST /api/v1/filing/submit
   */
  submitFiling(request: TaxFilingRequest): Observable<TaxFilingResponse> {
    return this.http.post<TaxFilingResponse>(
      `${this.apiUrl}/submit`,
      request,
      this.httpOptions
    );
  }

  /**
   * Retrieve all filings with optional filtering and pagination.
   * GET /api/v1/filing
   */
  getFilings(params?: { npwp?: string; filingType?: string; taxYear?: number; page?: number; pageSize?: number }): Observable<TaxFilingResponse[]> {
    let httpParams = new HttpParams();
    if (params?.npwp) {
      httpParams = httpParams.set('npwp', params.npwp);
    }
    if (params?.filingType) {
      httpParams = httpParams.set('filingType', params.filingType);
    }
    if (params?.taxYear) {
      httpParams = httpParams.set('taxYear', params.taxYear.toString());
    }
    if (params?.page) {
      httpParams = httpParams.set('page', params.page.toString());
    }
    if (params?.pageSize) {
      httpParams = httpParams.set('pageSize', params.pageSize.toString());
    }

    return this.http.get<TaxFilingResponse[]>(
      this.apiUrl,
      { ...this.httpOptions, params: httpParams }
    );
  }

  /**
   * Retrieve a specific filing by its ID.
   * GET /api/v1/filing/{filingId}
   */
  getFilingById(filingId: string): Observable<TaxFilingResponse> {
    return this.http.get<TaxFilingResponse>(
      `${this.apiUrl}/${filingId}`,
      this.httpOptions
    );
  }

  /**
   * Submit an amendment filing for an existing SPT.
   * POST /api/v1/filing/amend/{originalFilingId}
   */
  amendFiling(originalFilingId: string, request: TaxFilingRequest): Observable<TaxFilingResponse> {
    return this.http.post<TaxFilingResponse>(
      `${this.apiUrl}/amend/${originalFilingId}`,
      request,
      this.httpOptions
    );
  }

  /**
   * Validate a filing before submission.
   * POST /api/v1/filing/validate
   */
  validateFiling(request: TaxFilingRequest): Observable<{ isValid: boolean; errors: string[] }> {
    return this.http.post<{ isValid: boolean; errors: string[] }>(
      `${this.apiUrl}/validate`,
      request,
      this.httpOptions
    );
  }

  /**
   * Download the filing receipt (Bukti Penerimaan Elektronik).
   * GET /api/v1/filing/receipt/{filingId}
   */
  downloadFilingReceipt(filingId: string): Observable<Blob> {
    return this.http.get(
      `${this.apiUrl}/receipt/${filingId}`,
      {
        responseType: 'blob',
        headers: new HttpHeaders({ 'Accept': 'application/pdf' })
      }
    );
  }
}
