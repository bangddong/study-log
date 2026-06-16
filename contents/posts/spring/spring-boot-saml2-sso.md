---
title: Spring Boot SAML 2.0 SSO 연동 가이드
date: '2026-05-26'
tags:
  - Spring
series: null
emoji: "\U0001F510"
---

_Spring Boot 3.x + Spring Security 6.x 환경에서 SAML 2.0 SSO를 연동 내용을 정리했습니다. IdP 예시로 Microsoft Entra ID를 사용하지만, Okta·ADFS·Keycloak 등 SAML 2.0을 지원하는 모든 IdP에 동일하게 적용됩니다._


---


## SAML 기본 개념


| 용어                          | 설명                                     |
| --------------------------- | -------------------------------------- |
| **SP** (Service Provider)   | 실제 서비스를 제공하는 우리 시스템                    |
| **IdP** (Identity Provider) | 사용자 인증을 담당하는 중앙 시스템 (Entra ID, Okta 등) |
| **Assertion**               | IdP가 SP에게 발급하는 XML 형식의 인증 증명서          |
| **ACS URL**                 | IdP가 인증 결과를 POST하는 SP의 엔드포인트           |
| **NameID**                  | Assertion 안에서 사용자를 식별하는 값              |
| **RelayState**              | 인증 왕복 중 상태를 보존하는 파라미터 (예: 원래 보던 URL)   |
| **Metadata**                | SP와 IdP가 서로의 정보를 교환하는 XML 명세서          |


---


## 전체 인증 흐름 (SP-initiated SSO)


```javascript
1. 사용자가 서비스 접근 시도
2. SP: 세션 없음 확인 → /api/saml2/authenticate/{registrationId} 호출
3. SP: AuthnRequest XML 생성 → Base64 인코딩 → IdP 로그인 URL로 Redirect
4. 사용자: IdP(Entra ID) 로그인 페이지에서 인증
5. IdP: SAMLResponse(Assertion) 생성 + 서명 → ACS URL로 POST
6. SP: SAMLResponse 서명 검증 → 사용자 정보 추출 → 세션 생성
7. SP: RelayState(원래 URL)로 Redirect → 서비스 정상 진입
```


브라우저가 SP와 IdP 사이의 중개자 역할을 합니다. SP와 IdP는 직접 통신하지 않고, 모든 데이터가 브라우저를 통해 전달됩니다.


---


## 사전 준비


### 1. SP 서명용 키 쌍 생성


```bash
# 개인키 생성
openssl genrsa -out sp-private.key 2048

# 자체 서명 인증서 생성 (유효기간 3년)
openssl req -new -x509 -key sp-private.key \
  -out sp-certificate.crt \
  -days 1095 \
  -subj "/CN=my-app-saml-sp/O=MyCompany/C=KR"
```


생성된 파일:

- `sp-private.key` → 서버에만 보관. 절대 외부 노출 금지
- `sp-certificate.crt` → IdP 앱 등록 시 업로드 (공개해도 무방)

SAML SP 인증서는 CA 서명이 필요 없습니다. IdP에 직접 등록하는 방식이기 때문에 Self-signed로 충분합니다.


### 2. IdP 메타데이터 확보


IdP 관리자에게 **IdP 메타데이터 XML 파일**을 요청합니다.


| IdP                | 메타데이터 URL                                                                                        |
| ------------------ | ------------------------------------------------------------------------------------------------ |
| Microsoft Entra ID | `https://login.microsoftonline.com/{tenantId}/federationmetadata/2007-06/federationmetadata.xml` |
| Okta               | Okta Admin → 앱 → Sign On → Identity Provider metadata 링크                                         |
| Keycloak           | `https://{host}/realms/{realm}/protocol/saml/descriptor`                                         |
| ADFS               | `https://{adfs-host}/FederationMetadata/2007-06/FederationMetadata.xml`                          |


### 3. IdP에 SP 정보 등록


IdP 관리자에게 아래 정보를 전달합니다.


| 항목            | 값 예시                                                             |
| ------------- | ---------------------------------------------------------------- |
| Entity ID     | `https://myapp.company.com`                                      |
| ACS URL       | `https://myapp.company.com/api/login/saml2/sso/{registrationId}` |
| NameID Format | `emailAddress`                                                   |
| SP 인증서        | `sp-certificate.crt` 내용 (필요 시)                                   |


---


## 구현


### 1. 의존성 추가


```groovy
// build.gradle
dependencies {
    implementation 'org.springframework.security:spring-security-saml2-service-provider'
}
```


`opensaml` 아티팩트는 Maven Central에 없습니다. Shibboleth 저장소를 별도로 추가해야 합니다. 이 부분을 모르면 처음에 꼭 한번 막힙니다. 사내 Nexus 환경이라면 Shibboleth 레포를 Nexus에 proxy로 등록하는 것을 권장합니다.


```groovy
// settings.gradle
dependencyResolutionManagement {
    repositories {
        mavenCentral()
        maven { url "https://build.shibboleth.net/nexus/content/repositories/releases/" }
    }
}
```


### 2. 파일 배치


```javascript
src/main/resources/
  saml/
    sp-certificate.crt     ← SP 공개 인증서 (git 포함 가능)
    idp-metadata.xml        ← IdP 메타데이터 (git 포함 가능)
    sp-private.key          ← SP 개인키 (.gitignore 필수!)

서버 파일시스템:
  /APP/saml/
    sp-private.key          ← 배포 시 수동 배치
```


`sp-private.key`는 절대 git에 올라가면 안 됩니다. `.gitignore`에 반드시 추가합니다.


```javascript
src/main/resources/saml/*.key
```


### 3. SAML Properties 클래스


```java
@ConfigurationProperties(prefix = "saml")
@Getter
@Setter
public class SamlProperties {
    /** SAML assertion 속성명. 비어 있으면 NameID 사용 */
    private String userIdAttribute = "";
    /** 인증 성공 후 리다이렉트할 기본 URL */
    private String successRedirectUrl = "http://localhost:3000";
    /** redirect_uri 파라미터 허용 목록 */
    private List<String> allowedRedirectUris = new ArrayList<>();
    /** true이면 Form 로그인 차단 (prd SSO 강제용) */
    private boolean formLoginDisabled = false;
}
```


### 4. Spring Security 설정


Spring Security 6.x에서 삽질 포인트가 두 군데 있습니다. 아래 코드의 주석을 꼭 읽으세요.


```java
@Configuration
@RequiredArgsConstructor
@ConditionalOnProperty(
    prefix = "spring.security.saml2.relyingparty.registration.{registrationId}.assertingparty",
    name = "metadata-uri")
public class SamlSecurityConfig {

    private final CustomSamlAuthenticationSuccessHandler samlSuccessHandler;

    /**
     * SP-initiated 트리거 경로 커스터마이징.
     * 기본값 /saml2/authenticate/* → /api/saml2/authenticate/* 로 변경.
     * RelayState에 redirect_uri 파라미터를 담아 인증 후 원래 페이지로 복귀.
     */
    @Bean
    public Saml2AuthenticationRequestResolver saml2AuthenticationRequestResolver(
            RelyingPartyRegistrationRepository registrations) {
        OpenSaml4AuthenticationRequestResolver resolver =
                new OpenSaml4AuthenticationRequestResolver(registrations);
        resolver.setRequestMatcher(
                AntPathRequestMatcher.antMatcher("/api/saml2/authenticate/{registrationId}"));
        resolver.setRelayStateResolver(request -> {
            String redirectUri = request.getParameter("redirect_uri");
            return (redirectUri != null && !redirectUri.isBlank()) ? redirectUri : "";
        });
        return resolver;
    }

    /**
     * SAML 전용 Security Filter Chain.
     * - @Order(1): 일반 Security Filter Chain보다 먼저 처리
     * - authenticationRequestResolver를 명시적으로 주입해야 커스텀 경로가 적용됨
     *   (Spring Security 6.x에서 Bean 자동 감지 안 됨 — 이게 핵심 삽질 포인트)
     */
    @Bean
    @Order(1)
    public SecurityFilterChain samlFilterChain(
            HttpSecurity http,
            Saml2AuthenticationRequestResolver saml2AuthenticationRequestResolver) throws Exception {
        return http
                .securityMatcher("/api/saml2/**", "/api/login/saml2/**", "/api/logout/saml2/**")
                .cors(cors -> cors.disable())
                .csrf(csrf -> csrf.disable())
                .sessionManagement(session ->
                        session.sessionCreationPolicy(SessionCreationPolicy.IF_REQUIRED))
                .authorizeHttpRequests(auth -> auth.anyRequest().permitAll())
                .saml2Login(saml2 -> saml2
                        .authenticationRequestResolver(saml2AuthenticationRequestResolver) // 필수!
                        .loginProcessingUrl("/api/login/saml2/sso/{registrationId}")
                        .successHandler(samlSuccessHandler))
                .build();
    }
}
```


### 5. 인증 성공 핸들러


```java
@Component
@RequiredArgsConstructor
@Slf4j
public class CustomSamlAuthenticationSuccessHandler
        implements AuthenticationSuccessHandler {

    private final SessionService sessionService;
    private final SamlProperties samlProperties;

    @Override
    public void onAuthenticationSuccess(HttpServletRequest request,
            HttpServletResponse response,
            Authentication authentication) throws IOException {
        Saml2AuthenticatedPrincipal principal =
                (Saml2AuthenticatedPrincipal) authentication.getPrincipal();
        String userId = resolveUserId(principal);
        String userIp = NetworkUtil.getClientIP(request);
        log.info("SAML SSO 인증 성공 - userId: {}, ip: {}", userId, userIp);

        UserSessionVO userSession =
                sessionService.createUserSession(userId, null, userIp, false);
        if (userSession == null) {
            log.warn("SAML SSO - 미등록 사용자: {}", userId);
            response.sendRedirect("/sso-unauthorized");
            return;
        }

        HttpSession session = request.getSession();
        session.setAttribute(CommonConstants.HTTP_SESSION_KEY, userSession);
        response.sendRedirect(resolveRedirectUrl(request));
    }

    /**
     * Assertion에서 userId 추출.
     * 1순위: saml.user-id-attribute 설정값
     * 2순위: NameID
     * 이메일 형식이면 @ 앞부분만 추출
     */
    private String resolveUserId(Saml2AuthenticatedPrincipal principal) {
        String attrName = samlProperties.getUserIdAttribute();
        String raw;
        if (attrName != null && !attrName.isBlank()) {
            List<Object> attrValues = principal.getAttribute(attrName);
            if (attrValues != null && !attrValues.isEmpty()) {
                raw = attrValues.get(0).toString();
                return raw.contains("@") ? raw.split("@")[0] : raw;
            }
            log.warn("SAML assertion에 '{}' 속성 없음. NameID로 대체.", attrName);
        }
        raw = principal.getName();
        return raw.contains("@") ? raw.split("@")[0] : raw;
    }

    /**
     * 인증 후 이동할 URL 결정.
     * RelayState에 담긴 redirect_uri → 허용 목록 검증 후 사용.
     * 없거나 허용 목록 외의 값이면 기본 URL 사용.
     */
    private String resolveRedirectUrl(HttpServletRequest request) {
        String relayState = request.getParameter("RelayState");
        if (relayState != null && !relayState.isBlank()) {
            List<String> allowed = samlProperties.getAllowedRedirectUris();
            if (allowed.stream().anyMatch(relayState::startsWith)) {
                return relayState;
            }
            log.warn("RelayState '{}' 허용 목록 외. 기본 URL 사용.", relayState);
        }
        return samlProperties.getSuccessRedirectUrl();
    }
}
```


### 6. application.yml 설정


```yaml
spring:
  security:
    saml2:
      relyingparty:
        registration:
          {registrationId}:               # 식별자 (예: entra-id, okta, keycloak)
            entity-id: "{baseUrl}"         # SP Entity ID
            acs:
              location: "{baseUrl}/api/login/saml2/sso/{registrationId}"
            signing:
              credentials:
                - private-key-location: file:/APP/saml/sp-private.key
                  certificate-location: classpath:saml/sp-certificate.crt
            assertingparty:
              metadata-uri: "classpath:saml/idp-metadata.xml"
              # 또는 URL 직접 지정:
              # metadata-uri: "https://login.microsoftonline.com/{tenantId}/federationmetadata/..."

saml:
  # SAML assertion에서 userId로 사용할 속성명
  # 비워두면 NameID 사용
  # Entra ID 예시: "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
  user-id-attribute: ""
  # 인증 성공 후 기본 리다이렉트 URL
  success-redirect-url: "https://myapp.company.com"
  # redirect_uri 파라미터 허용 목록 (RelayState 검증용)
  allowed-redirect-uris:
    - "https://myapp.company.com"
    - "https://mobile.myapp.company.com"
  # true이면 Form 로그인 엔드포인트 차단 (prd 전용)
  form-login-disabled: false
```


---


## IdP별 주요 속성명 참고


### Microsoft Entra ID


| 속성       | URI                                                                  | 변경 가능성 |
| -------- | -------------------------------------------------------------------- | ------ |
| 이메일      | `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress` | 낮음     |
| 표시 이름    | `http://schemas.microsoft.com/identity/claims/displayname`           | 높음     |
| 불변 OID   | `http://schemas.microsoft.com/identity/claims/objectidentifier`      | 없음     |
| 이름 (UPN) | `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name`         | 낮음     |


### Okta / Keycloak / 일반 SAML IdP


| 속성     | URI                                            |
| ------ | ---------------------------------------------- |
| 이메일    | `urn:oid:0.9.2342.19200300.100.1.3` 또는 `email` |
| 이름     | `urn:oid:2.5.4.42` 또는 `firstName`              |
| 로그인 ID | IdP 설정에 따라 다름 (커스텀 속성 추가 가능)                   |


userId로 사용할 속성을 IdP 관리자와 협의해 **커스텀 클레임**으로 명시적으로 추가하는 것이 가장 안전합니다. Entra ID 기본 속성은 IdP 관리자가 구성을 바꾸면 값이 달라질 수 있습니다.


---


## 보안 체크리스트


```javascript
□ sp-private.key를 .gitignore에 추가했는가?
□ sp-private.key는 서버 파일시스템에만 존재하는가?
□ allowed-redirect-uris에 신뢰할 수 있는 URL만 등록했는가?
□ idp-metadata.xml의 X509Certificate가 최신인가? (IdP 인증서 만료 주의)
□ ACS URL이 HTTPS인가?
□ prd 환경에서 form-login-disabled: true로 설정했는가?
```


---


## Spring Security 6.x 주의사항


### authenticationRequestResolver 명시 주입 필수


Spring Security 6.x에서 `Saml2AuthenticationRequestResolver` Bean을 등록해도 자동으로 감지하지 않습니다. 직접 주입하지 않으면 커스텀 경로(`/api/saml2/authenticate/**`)가 적용되지 않고 기본 경로로 동작합니다.


```java
// ❌ 잘못된 예 — Bean 자동 감지 안 됨
.saml2Login(saml2 -> saml2
        .loginProcessingUrl("/api/login/saml2/sso/{registrationId}")
        .successHandler(samlSuccessHandler))

// ✅ 올바른 예 — 명시적으로 주입
.saml2Login(saml2 -> saml2
        .authenticationRequestResolver(saml2AuthenticationRequestResolver)
        .loginProcessingUrl("/api/login/saml2/sso/{registrationId}")
        .successHandler(samlSuccessHandler))
```


### @ConditionalOnProperty 사용 권장


`@ConditionalOnBean(RelyingPartyRegistrationRepository.class)`은 Bean 초기화 순서에 따라 조건이 의도대로 평가되지 않을 수 있습니다. 설정값 기반 조건으로 교체하는 것이 안전합니다.


```java
// ❌ 타이밍 이슈 가능성
@ConditionalOnBean(RelyingPartyRegistrationRepository.class)

// ✅ 명시적으로 설정값 기반으로 활성화
@ConditionalOnProperty(
    prefix = "spring.security.saml2.relyingparty.registration.{registrationId}.assertingparty",
    name = "metadata-uri")
```


---


## 트러블슈팅


| 증상                                   | 원인                                  | 해결                                                          |
| ------------------------------------ | ----------------------------------- | ----------------------------------------------------------- |
| `/api/saml2/authenticate/**` 404     | `authenticationRequestResolver` 미주입 | `saml2Login()`에 `.authenticationRequestResolver()` 추가       |
| `SamlSecurityConfig` 빈 미생성           | `@ConditionalOnBean` 타이밍 이슈         | `@ConditionalOnProperty`로 교체                                |
| `Could not resolve org.opensaml`     | Shibboleth 레포 누락                    | `settings.gradle`에 Shibboleth 레포 추가                         |
| `PKIX path building failed`          | 사내 SSL proxy로 인한 인증서 오류             | 사내 Nexus에 Shibboleth 레포 proxy 등록                            |
| `sp-private.key` not found           | classpath에 git-ignored 파일 없음        | `file:/APP/saml/sp-private.key`로 경로 변경                      |
| `SAXParseException: X509Certificate` | idp-metadata.xml CRLF 변환 오류         | Git `autocrlf=false` 또는 `.gitattributes`에 `*.xml binary` 추가 |
| 인증 후 세션 미수립                          | DB에 해당 userId 없음                    | `/sso-unauthorized` 페이지로 안내 또는 사용자 등록                       |

