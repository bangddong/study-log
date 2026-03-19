---
emoji: "🚀"
title: "중급 문법"
date: 2025-05-19 00:00:00
update: 2025-05-19 00:00:00
tags:
  - Spring
  - JPA
series: "Querydsl"
---

## 프로젝션과 결과 반환 - 기본

프로젝션 : select 대상 지정

### 프로젝션 대상이 하나

```java
List<String> result = queryFactory
        .select(member.username)
        .from(member)
        .fetch();
```

- 프로젝션 대상이 하나면 타입을 명확하게 지정할 수 있음
- 프로젝션 대상이 둘 이상이면 튜플이나 DTO로 조회

### 튜플 조회

프로젝션 대상이 둘 이상일 때 사용

`com.querydsl.core.Tuple`

```java
List<Tuple> result = queryFactory
			.select(member.username, member.age)
			.from(member)
			.fetch();

for (Tuple tuple : result) {
	String userName = tuple.get(member.username);
	Integer age = tuple.get(member.age);
	System.out.println("userName = " + userName);
	System.out.println("age = " + age);
}
```

**※ Tuple 객체는 엄연히 DataAccess 객체로 외부 계층으로 반환시 DTO로 변환하는걸 추천**

## 프로젝션과 결과 반환 - DTO 조회

순수 JPA에서 DTO 조회

**MemberDto**

```java
package stduy.querydsl.dto;

import lombok.Data;

@Data
public class MemberDto {

	private String username;
	private int age;

	public MemberDto(String username, int age) {
		this.username = username;
		this.age = age;
	}

}
```

### **순수 JPA에서 DTO 조회**

```java
List<MemberDto> result = em.createQuery(
		"select new stduy.querydsl.dto.MemberDto(m.username, m.age) from Member m", MemberDto.class)
	.getResultList();

for (MemberDto memberDto : result) {
	System.out.println("memberDto = " + memberDto);
}
```

- 순수 JPA에서 DTO 조회할 때는 new 명령어 사용
- DTO의 package 이름을 다 적어줘야해서 지저분
- 생성자 방식만 지원

### Querydsl 빈 생성(Bean population)

결과를 DT 반환할 때 사용하며 다음 세 가지 방법을 지원합니다.

- 프로퍼티 접근
- 필드 직접 접근
- 생성자 사용

**프로퍼티 접근 - Setter**

```java
List<MemberDto> result = queryFactory
	.select(Projections.bean(MemberDto.class, member.username, member.age))
	.from(member)
	.fetch();

for (MemberDto memberDto : result) {
	System.out.println("memberDto = " + memberDto);
}
```

**필드 직접 접근**

```java
**List<MemberDto> result = queryFactory
	.select(Projections.fields(MemberDto.class, member.username, member.age))
	.from(member)
	.fetch();

for (MemberDto memberDto : result) {
	System.out.println("memberDto = " + memberDto);
}**
```

**별칭이 다를 때**

```java
@Data
public class UserDto {

	private String name;
	private int age;
}
```

```java
@Test
public void findUserDto() throws Exception {
	QMember memberSub = new QMember("memberSub");
	List<UserDto> result = queryFactory
		.select(Projections.fields(UserDto.class,
			member.username.as("name"),
			ExpressionUtils.as(
				JPAExpressions
					.select(memberSub.age.max())
					.from(memberSub), "age")
		))
		.from(member)
		.fetch();

	for (UserDto userDto : result) {
		System.out.println("userDto = " + userDto);
	}
}
```

- 프로퍼티, 필드 접근 생성 방식에서 이름이 다를 때 해결 방안
- `ExpressionUtils.as(source, alias)`: 필드나, 서브 쿼리에 별칭 적용
- `username.as("memberName")`: 필드에 별칭 적용

**생성자 사용**

```java
@Test
public void findDtoByConstructor() throws Exception {
	List<MemberDto> result = queryFactory
		.select(Projections.constructor(MemberDto.class, member.username, member.age))
		.from(member)
		.fetch();

	for (MemberDto memberDto : result) {
		System.out.println("memberDto = " + memberDto);
	}
}
```

## 프로젝션과 결과 반환 - @QueryProjection

**생성자 + @QueryProjection**

```java
@QueryProjection <--------- 기존 생성자에 어노테이션 추가
public MemberDto(String username, int age) {
	this.username = username;
	this.age = age;
}
```

- 빌드 후 `QMemberDto` 생성 확인

**@QueryProjection 활용**

```java
List<MemberDto> result = queryFactory
	.select(new QMemberDto(member.username, member.age))
	.from(member)
	.fetch();

for (MemberDto memberDto : result) {
	System.out.println("memberDto = " + memberDto);
}
```

이 방법은 컴파일러로 타입을 체크할 수 있으므로 가장 안전한 방법입니다. 다만 DTO에 QueryDSL 어노테이션을 유지해야 하는 점과 DTO까지 Q 파일을 생성해야 하기 때문에 Dto에 Querydsl에 대한 의존성이 생기는 단점이 있습니다.

### **distinct**

```java
List<String> result = queryFactory
    .select(member.username).distinct()
    .from(member)
    .fetch();
```

## 동적 쿼리

동적 쿼리를 해결하는 방식은 두 가지가 있습니다

- BooleanBuilder
- Where 다중 파라미터 사용

### BooleanBuilder

```java
@Test
public void dynamicQuery_BooleanBuilder() throws Exception {
  String usernameParam = "member1";
	Integer ageParam = 10;

	List<Member> result = searchMember1(usernameParam, ageParam);
	assertThat(result.size()).isEqualTo(1);
}

private List<Member> searchMember1(String usernameCond, Integer ageCond) {
	// 필수 조건 필요시 초기값 설정 가능
	// BooleanBuilder builder = new BooleanBuilder(usernameCond.eq(조건));
	BooleanBuilder builder = new BooleanBuilder();
	if (usernameCond != null) {
		builder.and(member.username.eq(usernameCond));
	}
	if (ageCond != null) {
		builder.and(member.age.eq(ageCond));
	}
	return queryFactory
		.selectFrom(member)
		.where(builder)
		.fetch();
}
```

### Where 다중 파라미터 사용

```java
@Test
public void dynamicQuery_WhereParam() throws Exception {
  String usernameParam = "member1";
	Integer ageParam = 10;

	List<Member> result = searchMember2(usernameParam, ageParam);
	assertThat(result.size()).isEqualTo(1);
}

private List<Member> searchMember2(String usernameCond, Integer ageCond) {
	return queryFactory
		.selectFrom(member)
		.where(usernameEq(usernameCond), ageEq(ageCond))
		.fetch();
}

private BooleanExpression usernameEq(String usernameCond) {
	return usernameCond != null ? member.username.eq(usernameCond) : null;
}

private BooleanExpression ageEq(Integer ageCond) {
	return ageCond != null ? member.age.eq(ageCond) : null;
}

// 조합해서도 사용 가능하지만 null 체크는 주의해야 함
private BooleanExpression allEq(String usernameCond, Integer ageCond) {
  return usernameEq(usernameCond).and(ageEq(ageCond));
}
```

- `where` 조건에 `null` 값은 무시됨
- 메서드를 다른 쿼리에서도 **재활용** 가능
- 쿼리 자체의 가독성이 높아짐

## 수정, 삭제 벌크 연산

**쿼리 한 번으로 대량 데이터 수정**

```java
long count = queryFactory
			.update(member)
			.set(member.username, "비회원")
			.where(member.age.lt(28))
			.execute();
```

※ 영속성 컨텍스트에 있는 엔티티를 무시하고 실행되기 때문에 **배치 쿼리를 실행하고 나면 영속성 컨텍스트를 초기화** 하는 것이 안전

## SQL function 호출

SQL function은 JPA와 같이 Dialect에 등록된 내용만 호출할 수 있습니다.

**member ⇒ M으로 변경하는 replace 함수**

```java
String result = queryFactory
        .select(Expressions.stringTemplate("function('replace', {0}, {1}, {2})", 
member.username, "member", "M"))
        .from(member)
        .fetchFirst();
```

**소문자로 변경해서 비교**

```java
.select(member.username)
.from(member)
.where(member.username.eq(Expressions.stringTemplate("function('lower', {0})", 
member.username)))

// lower 같은 ansi 표준 함수들은 querydsl에 내장되어 있으니 다음과 같은 처리도 가능
.where(member.username.eq(member.username.lower()))
```

**이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗**

https://inf.run/Ybt69