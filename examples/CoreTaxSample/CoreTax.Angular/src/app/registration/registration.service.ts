import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface TaxRegistrationRequest {
  taxpayerName: string;
  npwp: string;
  idNumber: string;
  idType: string;
  address: string;
  businessType: string;
  email: string;
  phone: string;
}

export interface TaxRegistrationResponse {
  registrationId: string;
  npwp: string;
  status: string;
  registeredDate: string;
  taxpayerName: string;
  message: string;
}

export interface NpwpValidationResponse {
  npwp: string;
  isValid: boolean;
  taxpayerName: string;
}

@Injectable({
  providedIn: 'root'
})
export class RegistrationService {
  private readonly apiUrl = `${environment.apiBaseUrl}/api/v1/taxregistration`;

  private httpOptions = {
    headers: new HttpHeaders({
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    })
  };

  constructor(private http: HttpClient) {}

  /**
   * Register a new taxpayer in the CoreTax system.
   * POST /api/v1/taxregistration/register
   */
  registerTaxpayer(request: TaxRegistrationRequest): Observable<TaxRegistrationResponse> {
    return this.http.post<TaxRegistrationResponse>(
      `${this.apiUrl}/register`,
      request,
      this.httpOptions
    );
  }

  /**
   * Get the registration status for a given NPWP.
   * GET /api/v1/taxregistration/status/{npwp}
   */
  getRegistrationStatus(npwp: string): Observable<TaxRegistrationResponse> {
    return this.http.get<TaxRegistrationResponse>(
      `${this.apiUrl}/status/${npwp}`,
      this.httpOptions
    );
  }

  /**
   * Validate an NPWP number format and existence.
   * GET /api/v1/taxregistration/validate/{npwp}
   */
  validateNpwp(npwp: string): Observable<NpwpValidationResponse> {
    return this.http.get<NpwpValidationResponse>(
      `${this.apiUrl}/validate/${npwp}`,
      this.httpOptions
    );
  }

  /**
   * Update an existing taxpayer registration.
   * PUT /api/v1/taxregistration/update/{registrationId}
   */
  updateRegistration(registrationId: string, request: Partial<TaxRegistrationRequest>): Observable<TaxRegistrationResponse> {
    return this.http.put<TaxRegistrationResponse>(
      `${this.apiUrl}/update/${registrationId}`,
      request,
      this.httpOptions
    );
  }

  /**
   * Retrieve all registrations with optional filtering.
   * GET /api/v1/taxregistration/list
   */
  getRegistrations(params?: { status?: string; page?: number; pageSize?: number }): Observable<TaxRegistrationResponse[]> {
    let httpParams = new HttpParams();
    if (params?.status) {
      httpParams = httpParams.set('status', params.status);
    }
    if (params?.page) {
      httpParams = httpParams.set('page', params.page.toString());
    }
    if (params?.pageSize) {
      httpParams = httpParams.set('pageSize', params.pageSize.toString());
    }

    return this.http.get<TaxRegistrationResponse[]>(
      `${this.apiUrl}/list`,
      { ...this.httpOptions, params: httpParams }
    );
  }
}
