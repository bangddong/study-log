---
emoji: "🚀"
title: "스프링 데이터 JPA가 제공하는 Querydsl 기능"
date: 2025-08-11 00:00:00
update: 2025-08-11 00:00:00
tags:
  - Spring
  - JPA
series: "Querydsl"
---

이번 챕터에서 소개하는 기능은 제약이 커서 복잡한 실무 환경에서 사용하기에는 많이 부족합니다. 그래도 스프링 데이터에서 제공하는 기능이므로 간단히 소개하고, 왜 부족한지에 대해 설명드리려 합니다.

## 인터페이스 지원 - QuerydslPredicateExecutor

**QuerydslPredicateExecutor 인터페이스**

```java
public interface QuerydslPredicateExecutor<T> {
		Optional<T> findById(Predicate predicate);  
		Iterable<T> findAll(Predicate predicate);   
		long count(Predicate predicate);            
		boolean exists(Predicate predicate);        
    ...
}
```

`QuerydslPredicateExecutor`는 querydsl과 datajpa를 통해 동적 쿼리를 사용할 수 있도록 지원해주는 기능입니다.

```java
 Iterable result = memberRepository.findAll(
        member.age.between(10, 40)
        .and(member.username.eq("member1"))
 );
```

### 한계점

- 명시적 조인은 사용 불가능하며 경로 표현식에 의한 묵시적 조인만 가능 (inner join)
- 클라어인트가 Querydsl에 의존. 서비스 클래스가 Querydsl이라는 구현 기술에 의존해야 함

  (Controller, Service와 같은 계층에서 predicate 구현체를 만들어 넘겨야함)

- 복잡한 실무환경에서 사용하기에는 한계가 명확함.

## Querydsl Web 지원

**컨트롤러 예제**

```java
@GetMapping("test")
public String querydsl_web(@QuerydslPredicate(root = Member.class) Predicate predicate) {
	...
}
```

위 API 조회시 파라미터에 Member 객체의 필드를 전달하면 자동으로 predicate에 equals 문을 바인딩시켜줍니다.

### 한계점

- 단순 조건만 가능
- 조건을 커스텀하는 기능이 복잡하고 명시적이지 않음
- 컨트롤러가 Querydsl에 의존
- 복잡한 실무환경에서 사용하기에는 한계가 명확

## 리포지토리 지원 - QuerydslRepositorySupport

**QuerydslRepositorySupport extends**

```java
public class MemberRepositoryImpl 
	extends QuerydslRepositorySupport 
	implements MemberRepositoryCustom {
		public MemberRepositoryImpl() {
			super(Member.class);
		}
		...
}
```

Repository  사용

```java
@Override
	public List<MemberTeamDto> search(MemberSearchCondition condition) {
		List<MemberTeamDto> fetch = from(member) // from절부터 바로 사용!
			.leftJoin(member.team, team)
			.where(
				usernameEq(condition.getUsername()),
				teamNameEq(condition.getTeamName()),
				ageGoe(condition.getAgeGoe()),
				ageLoe(condition.getAgeLoe())
			)
			.select(new QMemberTeamDto(
				member.id,
				member.username,
				member.age,
				team.id,
				team.name))
			.fetch();
}
```

### 장점

- `getQuerydsl().applyPagination()` 스프링 데이터가 제공하는 페이징을 Querydsl로 편리하게 변환가능 (단 Sort는 오류발생)
- `from()`으로 시작가능(최근에는 QueryFactory를 사용해서 `select()`로 시작하는 것이 더 명시적)
- EntityManger 제공

### 한계

- Querydsl 3.x 버전을 대상으로 만듬
- Querydsl 4.x에 나온 JPAQueryFactory로 시작할 수 없음
    - select로 시작할 수 없음(from으로 시작해야 함)
- `QueryFactory`를 제공하지 않음
- 스프링 데이터 Sort 기능이 정상 동작하지 않음

## Querydsl 지원 클래스 직접 만들기

스프링 데이터가 제공하는 `QuerydslRepositorySupport`가 지닌 한계를 극복하기 위해 직접 Querydsl 지원 클래스를 만들어보겠습니다.

### 장점

- 스프링 데이터가 제공하는 페이징을 편리하게 변환
- 페이징과 카운트 쿼리 분리 가능
- 스프링 데이터 Sort 지원
- `select()`, `selectFrom`으로 시작 가능
- `EntityManager`, `QueryFactory` 제공

**Querydsl4RepositorySupport**

```java
package stduy.querydsl.repository.support;

import java.util.List;
import java.util.function.Function;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.support.JpaEntityInformation;
import org.springframework.data.jpa.repository.support.JpaEntityInformationSupport;
import org.springframework.data.jpa.repository.support.Querydsl;
import org.springframework.data.querydsl.SimpleEntityPathResolver;
import org.springframework.data.support.PageableExecutionUtils;
import org.springframework.stereotype.Repository;
import org.springframework.util.Assert;

import com.querydsl.core.types.EntityPath;
import com.querydsl.core.types.Expression;
import com.querydsl.core.types.dsl.PathBuilder;
import com.querydsl.jpa.impl.JPAQuery;
import com.querydsl.jpa.impl.JPAQueryFactory;

import jakarta.annotation.PostConstruct;
import jakarta.persistence.EntityManager;

@Repository
public abstract class Querydsl4RepositorySupport {
	private final Class domainClass;
	private Querydsl querydsl;
	private EntityManager entityManager;
	private JPAQueryFactory queryFactory;

	public Querydsl4RepositorySupport(Class<?> domainClass) {
		Assert.notNull(domainClass, "Domain class must not be null!");
		this.domainClass = domainClass;
	}

	@Autowired
	public void setEntityManager(EntityManager entityManager) {
		Assert.notNull(entityManager, "EntityManager must not be null!");
		JpaEntityInformation entityInformation =
			JpaEntityInformationSupport.getEntityInformation(domainClass, entityManager);
		SimpleEntityPathResolver resolver = SimpleEntityPathResolver.INSTANCE;
		EntityPath path = resolver.createPath(entityInformation.getJavaType());
		this.entityManager = entityManager;
		this.querydsl = new Querydsl(entityManager, new PathBuilder<>(path.getType(), path.getMetadata()));
		this.queryFactory = new JPAQueryFactory(entityManager);
	}

	@PostConstruct
	public void validate() {
		Assert.notNull(entityManager, "EntityManager must not be null!");
		Assert.notNull(querydsl, "Querydsl must not be null!");
		Assert.notNull(queryFactory, "QueryFactory must not be null!");
	}

	protected JPAQueryFactory getQueryFactory() {
		return queryFactory;
	}

	protected Querydsl getQuerydsl() {
		return querydsl;
	}

	protected EntityManager getEntityManager() {
		return entityManager;
	}

	protected <T> JPAQuery<T> select(Expression<T> expr) {
		return getQueryFactory().select(expr);
	}

	protected <T> JPAQuery<T> selectFrom(EntityPath<T> from) {
		return getQueryFactory().selectFrom(from);
	}

	protected <T> Page<T> applyPagination(Pageable pageable,
		Function<JPAQueryFactory, JPAQuery> contentQuery) {
		JPAQuery jpaQuery = contentQuery.apply(getQueryFactory());
		List<T> content = getQuerydsl().applyPagination(pageable,
			jpaQuery).fetch();
		return PageableExecutionUtils.getPage(content, pageable,
			jpaQuery::fetchCount);
	}

	protected <T> Page<T> applyPagination(Pageable pageable,
		Function<JPAQueryFactory, JPAQuery> contentQuery, Function<JPAQueryFactory,
			JPAQuery> countQuery) {
		JPAQuery jpaContentQuery = contentQuery.apply(getQueryFactory());
		List<T> content = getQuerydsl().applyPagination(pageable,
			jpaContentQuery).fetch();
		JPAQuery countResult = countQuery.apply(getQueryFactory());
		return PageableExecutionUtils.getPage(content, pageable,
			countResult::fetchCount);
	}
}
```

**Querydsl4RepositorySupport 사용 코드**

```java
package stduy.querydsl.repository;

import static org.springframework.util.StringUtils.*;
import static stduy.querydsl.entity.QMember.*;

import java.util.List;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.support.PageableExecutionUtils;
import org.springframework.stereotype.Repository;

import com.querydsl.core.types.dsl.BooleanExpression;
import com.querydsl.jpa.impl.JPAQuery;

import stduy.querydsl.dto.MemberSearchCondition;
import stduy.querydsl.entity.Member;
import stduy.querydsl.repository.support.Querydsl4RepositorySupport;

@Repository
public class MemberTestRepository extends Querydsl4RepositorySupport {

	public MemberTestRepository() {
		super(Member.class);
	}

	public List<Member> basicSelect() {
		return select(member)
			.from(member)
			.fetch();
	}

	public List<Member> basicSelectFrom() {
		return selectFrom(member)
			.fetch();
	}

	public Page<Member> searchPageByApplyPage(MemberSearchCondition condition, Pageable pageable) {
		JPAQuery<Member> query = selectFrom(member)
			.where(usernameEq(condition.getUsername()),
				teamNameEq(condition.getTeamName()),
				ageGoe(condition.getAgeGoe()),
				ageLoe(condition.getAgeLoe())
			);

		List<Member> content = getQuerydsl().applyPagination(pageable, query).fetch();

		return PageableExecutionUtils.getPage(content, pageable, query::fetchCount);
	}

	public Page<Member> applyPagination(MemberSearchCondition condition, Pageable pageable) {
		return applyPagination(pageable, query ->
			query.selectFrom(member)
				.where(usernameEq(condition.getUsername()),
					teamNameEq(condition.getTeamName()),
					ageGoe(condition.getAgeGoe()),
					ageLoe(condition.getAgeLoe())
				)
		);
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

}
```

**이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗**

https://inf.run/Ybt69