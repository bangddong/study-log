---
emoji: "🚀"
title: "순수 JPA와 Querydsl 비교"
date: 2025-05-19 00:00:00
update: 2025-05-19 00:00:00
tags:
  - Spring
  - JPA
series: "Querydsl"
---

## 순수 JPA 리포지토리와 Querydsl

### **순수 JPA 리포지토리**

```java
package stduy.querydsl.repository;

import static stduy.querydsl.entity.QMember.*;

import java.util.List;
import java.util.Optional;

import org.springframework.stereotype.Repository;

import com.querydsl.jpa.impl.JPAQueryFactory;

import jakarta.persistence.EntityManager;
import lombok.RequiredArgsConstructor;
import stduy.querydsl.entity.Member;
import stduy.querydsl.entity.QMember;

@Repository
@RequiredArgsConstructor
public class MemberJpaRepository {

	private final EntityManager em;
	private final JPAQueryFactory queryFactory;

	public void save(Member member) {
		em.persist(member);
	}

	public Optional<Member> findById(Long id) {
		Member findMember = em.find(Member.class, id);
		return Optional.ofNullable(findMember);
	}

	public List<Member> findAll() {
		return em.createQuery("select m from Member m", Member.class)
			.getResultList();
	}

	public List<Member> findByUserName(String username) {
		return em.createQuery("select m from Member m where m.username = :username", Member.class)
			.setParameter("username", username)
			.getResultList();
	}
}
```

### **순수 JPA 리포지토리 테스트**

```java
package stduy.querydsl.repository;

import static org.assertj.core.api.Assertions.*;
import static org.junit.jupiter.api.Assertions.*;

import java.util.List;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import jakarta.persistence.EntityManager;
import jakarta.transaction.Transactional;
import stduy.querydsl.entity.Member;

@SpringBootTest
@Transactional
class MemberJpaRepositoryTest {

	@Autowired
	EntityManager em;

	@Autowired
	MemberJpaRepository memberJpaRepository;

	@Test
	public void basicTest() throws Exception {
	    Member member = new Member("member1", 10);
		memberJpaRepository.save(member);

		Member findMember = memberJpaRepository.findById(member.getId()).get();
		assertEquals(member, findMember);

		List<Member> result1 = memberJpaRepository.findAll();
		assertThat(result1).containsExactly(member);

		List<Member> result2 = memberJpaRepository.findByUserName("member1");
		assertThat(result2).containsExactly(member);
	}
}
```

### **Querydsl 사용**

```java
public List<Member> findAll_Querydsl() {
		return queryFactory
			.selectFrom(member)
			.fetch();
}

public List<Member> findByUserName_Querydsl(String username) {
		return queryFactory
			.selectFrom(member)
			.where(member.username.eq(username))
			.fetch();
	}
```

### **Querydsl 테스트 추가**

```java
@Test
public void basicQuerydslTest() throws Exception {
	Member member = new Member("member1", 10);
	memberJpaRepository.save(member);

	List<Member> result1 = memberJpaRepository.findAll_Querydsl();
	assertThat(result1).containsExactly(member);

	List<Member> result2 = memberJpaRepository.findByUserName_Querydsl("member1");
	assertThat(result2).containsExactly(member);
}
```

※ 스프링이 주입해주는 엔티티 매니저는 실제 동작 시점에 진짜 엔티티 매니저를 찾아주는 **프록시용** 가짜 엔티티 매니저입니다. 이 프록시는 실제 사용 시점에 트랜잭션 단위로 실제 엔티티 매니저(영속성 컨텍스트)를 할당해주니 동시성 문제는 발생하지 않습니다.

‣

## 동적 쿼리와 성능 최적화 조회 - Builder 사용

**MemberTeamDto - 조회 최적화용 DTO**

```java
package stduy.querydsl.dto;

import com.querydsl.core.annotations.QueryProjection;
import lombok.Data;

@Data
public class MemberTeamDto {
	private Long memberId;
	private String username;
	private int age;
	private Long teamId;
	private String teamName;

	@QueryProjection
	public MemberTeamDto(Long memberId, String username, int age, Long teamId, String teamName) {
		this.memberId = memberId;
		this.username = username;
		this.age = age;
		this.teamId = teamId;
		this.teamName = teamName;
	}
}

```

- `@QueryProject`을 사용하니 `QMemberTeamDto`를 생성하기 위해 build 실행
- 해당 어노테이션을 사용하면 DTO가 querydsl에 의존하게 되니 이게 싫다면 `Projection.bean(), fields(), constructor()`를 사용



**회원 검색 조건**

```java
package stduy.querydsl.dto;

import lombok.Data;

@Data
public class MemberSearchCondition {

	private String username;
	private String teamName;
	private Integer ageGoe;
	private Integer ageLoe;
}
```

### **동적쿼리 - Builder 사용**

```java
public List<MemberTeamDto> searchByBuilder(MemberSearchCondition condition) {
		BooleanBuilder builder = new BooleanBuilder();
		if (hasText(condition.getUsername())) {
			builder.and(member.username.eq(condition.getUsername()));
		}
		if (hasText(condition.getTeamName())) {
			builder.and(member.team.name.eq(condition.getTeamName()));
		}
		if (condition.getAgeGoe() != null) {
			builder.and(member.age.goe(condition.getAgeGoe()));
		}
		if (condition.getAgeLoe() != null) {
			builder.and(member.age.loe(condition.getAgeLoe()));
		}
	
		return queryFactory
			.select(new QMemberTeamDto(
				member.id.as("memberId"),
				member.username,
				member.age,
				team.id.as("teamId"),
				team.name.as("teamName")))
			.from(member)
			.leftJoin(member.team, team)
			.where(builder)
			.fetch();
	}
```

### **조회 예제 테스트**

```java
@Test
public void searchTest() throws Exception {
	Team teamA = new Team("teamA");
	Team teamB = new Team("teamB");
	em.persist(teamA);
	em.persist(teamB);

	Member member1 = new Member("member1", 10, teamA);
	Member member2 = new Member("member2", 20, teamA);
	Member member3 = new Member("member3", 30, teamB);
	Member member4 = new Member("member4", 40, teamB);
	em.persist(member1);
	em.persist(member2);
	em.persist(member3);
	em.persist(member4);

	MemberSearchCondition condition = new MemberSearchCondition();
	condition.setAgeGoe(35);
	condition.setAgeLoe(40);
	condition.setTeamName("teamB");

	List<MemberTeamDto> result = memberJpaRepository.searchByBuilder(condition);

	assertThat(result).extracting("username").containsExactly("member4");
}
```

※ 개발 중 여러가지 이유로 condition 조건이 없을 경우 join 데이터를 모두 가져오니 데이터가 많이 쌓일 수 있을 경우 기본 조건을 걸어두는 것도 방법

## 동적 쿼리와 성능 최적화 조회 - Where 절 파라미터 사용

### **Where절에 파라미터를 사용한 예제**

```java
public List<MemberTeamDto> search(MemberSearchCondition condition) {
	return queryFactory
		.select(new QMemberTeamDto(
			member.id,
			member.username,
			member.age,
			team.id,
			team.name))
		.from(member)
		.leftJoin(member.team, team)
		.where(
			usernameEq(condition.getUsername()),
			teamNameEq(condition.getTeamName()),
			ageGoe(condition.getAgeGoe()),
			ageLoe(condition.getAgeLoe())
		)
		.fetch();
}

private BooleanExpression usernameEq(String username) {
	return hasText(username) ? member.username.eq(username) : null;
}

private BooleanExpression teamNameEq(String teamName) {
	return hasText(teamName) ? member.team.name.eq(teamName) : null;
}

private BooleanExpression ageGoe(Integer ageGoe) {
	return ageGoe != null ? member.age.goe(ageGoe) : null;
}

private BooleanExpression ageLoe(Integer ageLoe) {
	return ageLoe != null ? member.age.loe(ageLoe) : null;
}
```

### **where 절에 파라미터 방식을 사용해 조건 재사용**

```java
public List<Member> findMember(MemberSearchCondition condition) {
	return queryFactory
		.selectFrom(member)
		.leftJoin(member.team, team)
		.where(
			usernameEq(condition.getUsername()),
			teamNameEq(condition.getTeamName()),
			ageGoe(condition.getAgeGoe()),
			ageLoe(condition.getAgeLoe())
		)
		.fetch();
}
```

## 조회 API 컨트롤러 개발

편리한 데이터 확인을 위해 샘플 데이터를 추가합니다. 샘플 데이터 추가가 테스트 케이스 실행에 영향을 주지 않도록 다음과 같이 프로파일을 설정 후 진행합니다.

```java
// src/main/resources/application.yml (local)
spring:
  profiles:
    active: local
    
// src/test/resources/application.yml (test)
spring:
  profiles:
    active: test
```

**샘플데이터**

```java
package stduy.querydsl.controller;

import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

import jakarta.annotation.PostConstruct;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import stduy.querydsl.entity.Member;
import stduy.querydsl.entity.Team;

@Profile("local")
@Component
@RequiredArgsConstructor
public class InitMember {

	private final InitMemberService initMemberService;

	@PostConstruct
	public void init() {
		initMemberService.init();
	}

	@Component
	static class InitMemberService {
		@PersistenceContext
		private EntityManager em;

		@Transactional
		public void init() {
			Team teamA = new Team("Team A");
			Team teamB = new Team("Team B");
			em.persist(teamA);
			em.persist(teamB);

			for (int i = 0; i < 100; i++) {
				Team selectedTeam = i % 2 == 0 ? teamA : teamB;
				em.persist(new Member("member" + i, i , selectedTeam));
			}
		}
	}
}
```

**조회 컨트롤러**

```java
package stduy.querydsl.controller;

import java.util.List;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import lombok.RequiredArgsConstructor;
import stduy.querydsl.dto.MemberSearchCondition;
import stduy.querydsl.dto.MemberTeamDto;
import stduy.querydsl.repository.MemberJpaRepository;

@RestController
@RequiredArgsConstructor
public class MemberController {

	private final MemberJpaRepository memberJpaRepository;

	@GetMapping("/v1/members")
	public List<MemberTeamDto> searchMemberV1(MemberSearchCondition condition) {
		return memberJpaRepository.search(condition);
	}
}
```

이후 [localhost:8080/v1/members](http://localhost:8080/v1/members) 실행하며 테스트 진행

**이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗**

https://inf.run/Ybt69