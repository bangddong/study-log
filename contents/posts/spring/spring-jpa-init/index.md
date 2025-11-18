---
emoji: "🚀"
title: "Spring JPA 시작하기"
date: 2024-08-20 13:55:00
update: 2024-08-20 13:55:00
tags:
  - Spring
  - JPA
series: "스프링 부트와 JPA 활용 1"
---

## 프로젝트 생성

Intellij 기준

Type : Gradle - Groovy

JDK : 17

Packaging: Jar

Dependencies

- Spring Boot : 3.4.3
- Spring Web
- Spring Data JPA
- H2 Database
- Thymeleaf
- Lombok

Lombok 플러그인 설치 후 환경설정 내 Annotation Processors 내 Enable annotation processing 활성화

## Database 설정

경량 DB인 H2 Database 설치

https://www.h2database.com

설치 후 실행시 h2 DB 웹 콘솔창이 뜸. 아래와 같이 입력 후 접속

![spring-jpa-init-1.png](images/spring-jpa-init-1.png)

정상 연결 확인 되었으면 파일 생성 확인 후 이후부터는 jdbc:h2:tcp://localhost/~/jpashop으로 접속

### application.yml 설정

기존 [application.properties](http://application.properties) 삭제 후 진행

```java
spring:
  datasource:
    url: jdbc:h2:tcp://localhost/~/jpashop
    username: sa
    password:
    driver-class-name: org.h2.Driver

  jpa:
    hibernate:
      ddl-auto: create
    properties:
      hibernate:
        format_sql: true
        dialect: org.hibernate.dialect.H2Dialect

logging:
  level:
    org.hibernate.SQL: debug
```

### 테스트를 위한 파일 생성 (Entity, Repository)

Member.java

```java
@Entity
@Getter
@Setter
public class Member {
	
	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;
	private String username;
	
}
```

MemberRepository.java

```java
@Repository
public class MemberRepository {

	@PersistenceContext
	private EntityManager em;
	
	private Long save(Member member){
		em.persist(member);
		return member.getId();
	}
	
	public Member find(Long id) {
		return em.find(Member.class, id);
	}

}
```

### 테스트 및 확인

MemberRepositoryTest.java

```java
@RunWith(SpringRunner.class)
@SpringBootTest
public class MemberRepositoryTest {

	@Autowired
	MemberRepository memberRepository;

	@Test
	@Transactional
	// 실데이터 확인 필요시 주석해제
	// @Rollback(false)
	public void testMember() throws Exception {
		// given
		Member member = new Member();
		member.setUsername("memberA");

		// when
		Long saveId = memberRepository.save(member);
		Member findMember = memberRepository.find(saveId);

		// then
		assertEquals(findMember.getId(), member.getId());
		assertEquals(findMember.getUsername(), member.getUsername());
		assertEquals(findMember, member);
	}
}
```

- JUnit4 관련 설정

  기본적으로 JUnit5를 사용하고 있으니 JUnit4로 돌리려면 build.gradle에 하단 내용 추가

    ```java
    testImplementation("org.junit.vintage:junit-vintage-engine") {
        exclude group: "org.hamcrest", module: "hamcrest-core"
    }
    ```

![spring-jpa-init-2.png](images/spring-jpa-init-2.png)

![spring-jpa-init-3.png](images/spring-jpa-init-3.png)

- JPA 로깅설정
    - 1번 방법

      application.yml 내 아래 구문 추가
      `org.hibernate.orm.jdbc.bind: trace`

    - 2번 방법

      라이브러리 설치 (별도 설정 없음)
      `implementation 'com.github.gavlyukovskiy:p6spy-spring-boot-starter:1.9.0'`

이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗

    https://inf.run/4Sbno