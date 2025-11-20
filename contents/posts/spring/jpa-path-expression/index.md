---
emoji: "🚀"
title: "경로표현식"
date: 2025-02-27 00:00:00
update: 2025-02-27 00:00:00
tags:
  - Spring
  - JPA
series: "JPA 기본"
---

경로표현식이란 `JPQL`에서 .(점)을 찍어 객체 그래프를 탐색하는 것입니다.

```java
select m.username -> 상태 필드
	from Member m
	join m.team t   -> 단일 값 연관 필드
	join m.orders o -> 컬렉션 값 연관 필드
where t.name = '팀A'
```

## 경로 표현식 용어 정리

- 상태 필드 : 단순히 값을 저장하기 위한 필드 (특정 컬럼)
- 연관 필드 : 연관 관계를 위한 필드
    - 단일 값 연괄 필드

      @ManToOne, @OneToOne, 대상이 엔티티(ex: m.team)

    - 컬렉션 값 연관 필드

      @OneToMany, @ManyToMany, 대상이 컬렉션(ex. m.orders)


## 경로 표현식 특징

- 상태 필드: 경로 탐색의 끝, 추가 탐색 불가
- 단일 값 연관 경로: 묵시적 내부 조인(inner join) 발생, 추가 탐색 가능
- 컬렉션 값 연관 경로: 묵시적 내부 조인 발생, 추가 탐색 불가
    - FROM 절에서 명시적 조인을 통해 별칭을 얻으면 별칭을 통해 탐색 가능

        ```java
        ❌ member 추가 탐색 불가
        select t.members from Team t
        
        ✅ 명시적 조인을 통해 추가 탐색
        select m.username from Team t join t.members m
        ```

- `묵시적 내부 조인?`

    ```java
    // Member 내 Team을 조회했으나 경로 표현식에 의해 묵시적으로 SQL 조인 발생
    String query = "select m.team from Member m";
    ...
    Hibernate: 
        /* select
            m.team 
        from
            Member m */ select
                t1_0.id,
                t1_0.name 
            from
                Member m1_0 
            join
                Team t1_0 
                    on t1_0.id=m1_0.TEAM_ID
    ```


### 경로 표현식 예제

✅ select [o.member.team](http://o.member.team) from Order o

✅ select t.members from Team

❌ select t.members.username from Team t

✅ select m.username from Team t join t.members m

### 경로 탐색을 사용한 묵시적 조인 시 주의사항

- 항상 내부 조인
- 컬렉션은 경로 탐색의 끝, 명시적 조인을 통해 별칭을 얻어야 함
- 경로 탐색은 주로 SELECT, WHERE 절에서 사용하지만 묵시적 조인으로 인해 SQL의 FROM (JOIN) 절에 영향을 줌
- `가급적 묵시적 조인 대신에 명시적 조인 사용`
- `조인은 SQL 튜닝에 중요 포인트로 묵시적 조인은 조인 발생 상황을 한 눈에 파악하기 어려움`

**~~쉽게 생각해 그냥 명시적 조인만 써라~~**