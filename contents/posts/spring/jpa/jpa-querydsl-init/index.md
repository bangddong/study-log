---
emoji: "🚀"
title: "프로젝트 환경설정"
date: 2025-05-15 00:00:00
update: 2025-05-15 00:00:00
tags:
  - Spring
  - JPA
series: "Querydsl"
---

- Project: Gradle - Groovy
- Spring Web, JPA, H2, Lombok

## Querydsl 설정 및 검증

`build.gradle`에 주석을 참고하여 querydsl 설정 추가

```java
plugins {
    id 'java'
    id 'org.springframework.boot' version '3.4.5'
    id 'io.spring.dependency-management' version '1.1.7'
}

group = 'stduy'
version = '0.0.1-SNAPSHOT'

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(17)
    }
}

configurations {
    compileOnly {
        extendsFrom annotationProcessor
    }
}

repositories {
    mavenCentral()
}

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation 'org.springframework.boot:spring-boot-starter-web'
    compileOnly 'org.projectlombok:lombok'
    runtimeOnly 'com.h2database:h2'
    annotationProcessor 'org.projectlombok:lombok'
    testImplementation 'org.springframework.boot:spring-boot-starter-test'
    testRuntimeOnly 'org.junit.platform:junit-platform-launcher'

    //Querydsl 추가
    implementation 'com.querydsl:querydsl-jpa:5.1.0:jakarta'
    annotationProcessor "com.querydsl:querydsl-apt:${dependencyManagement.importedProperties['querydsl.version']}:jakarta"
    annotationProcessor "jakarta.annotation:jakarta.annotation-api"
    annotationProcessor "jakarta.persistence:jakarta.persistence-api"
}

tasks.named('test') {
    useJUnitPlatform()
}

clean {
    delete file('src/main/generated')
}
```

**※ SQL Injection 관련 CVE-2024-49203 보안 경고는 아래 github 참고하여 해결 가능함**

https://github.com/querydsl/querydsl/issues/3757

이후 gradle ⇒ clean ⇒ build시 Q Class 생성

![image.png](images/img.png)

**※ Q Class 미생성시 Intellij의 Annotation Processor 설정 확인**

### 테스트 케이스로 검증

```java
@SpringBootTest
@Transactional
class QuerydslApplicationTests {

	@Autowired
	EntityManager em;

	@Test
	void contextLoads() {
		Hello hello = new Hello();
		em.persist(hello);

		JPAQueryFactory query = new JPAQueryFactory(em);
		QHello qHello = QHello.hello;

		Hello result = query
			.selectFrom(qHello)
			.fetchOne();

		assertThat(result).isEqualTo(hello);
		assertThat(result.getId()).isEqualTo(hello.getId());
	}

}
```

## H2 데이터베이스 세팅

최초 파일모드로 Database 생성 이후 TCP 접속

- jdbc:h2:~/querydsl
- jdbc:h2:tcp://localhost/~/querydsl

## 스프링 부트 설정 - JPA, DB

`application.yml`

```java
spring:
  datasource:
    url: jdbc:h2:tcp://localhost/~/querydsl
    username: sa
    password:
    driver-class-name: org.h2.Driver

  jpa:
    hibernate:
      ddl-auto: create
    properties:
      hibernate:
        #show_sql: true
        format_sql: true
  logging.level:
    org.hibernate.SQL: debug
    #org.hibernate.type: trace
```

`build.gradle`

```java
implementation("com.github.gavlyukovskiy:p6spy-spring-boot-starter:1.11.0")
```

**이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗**

https://inf.run/Ybt69