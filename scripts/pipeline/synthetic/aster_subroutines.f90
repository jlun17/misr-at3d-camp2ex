!-------------------------------------------------------------------
!
!                           SUBROUTINES
!
!-------------------------------------------------------------------
subroutine perimeter(ncol,nline,iclouds,tflag, operi)
   integer*4                           ,intent(in) :: ncol,nline
   integer*4, dimension(1:ncol,1:nline),intent(in) :: iclouds
   integer*4                           ,intent(in) :: tflag
   integer*4, dimension(1:tflag)       ,intent(out):: operi  

   !f2py intent(in) :: iclouds, tflag
   !f2py intent(hide), depend(iclouds) :: nline = shape(iclouds,0), ncol = shape(iclouds,1)
   !f2py intent(out) :: operi

   integer*4     :: i,j,k, cnt
   integer*4, dimension(:,:), allocatable          :: clouds
   
   allocate(clouds(0:ncol+1,0:nline+1))
   clouds=0
   clouds(1:ncol,1:nline)=iclouds(1:ncol,1:nline)
   operi=0  
   do j=1, nline
      do i=1, ncol
         if (clouds(i,j) < 1) cycle
         cnt=0
	      if (clouds(i+1,j) < 1) cnt=cnt+1
	      if (clouds(i-1,j) < 1) cnt=cnt+1
	      if (clouds(i,j+1) < 1) cnt=cnt+1
	      if (clouds(i,j-1) < 1) cnt=cnt+1
	      operi(clouds(i,j))=operi(clouds(i,j))+cnt
      end do
   end do
   if (allocated(clouds)) deallocate(clouds)
end subroutine perimeter

!::::::::::::::::::::::::::::::::::::::::::::::::::
!       subroutine maskoff
!::::::::::::::::::::::::::::::::::::::::::::::::::
subroutine maskoff(imask,nline,ncol,corners, omask)
implicit none
integer*4                            :: nline, ncol
integer*1, dimension(1:ncol,1:nline) :: imask
integer*1, dimension(1:ncol,1:nline) :: omask
integer*4, dimension(1:4,1:2)        :: corners

integer*4                   :: i,j,k 
real*8                      :: a1,b1,a2,b2,a3,b3,a4,b4,y1,y2,y3,y4
corners(:,:)=-corners(:,:)
write(*,*) corners(1,:)
write(*,*) corners(2,:)
write(*,*) corners(3,:)
write(*,*) corners(4,:)
a1=dble(corners(1,2)-corners(2,2))/dble(corners(1,1)-corners(2,1))
b1=dble(corners(1,2)*corners(2,1)-corners(2,2)*corners(1,1))/dble(corners(2,1)-corners(1,1))

a2=dble(corners(1,2)-corners(3,2))/dble(corners(1,1)-corners(3,1))
b2=dble(corners(1,2)*corners(3,1)-corners(3,2)*corners(1,1))/dble(corners(3,1)-corners(1,1))

a3=dble(corners(2,2)-corners(4,2))/dble(corners(2,1)-corners(4,1))
b3=dble(corners(2,2)*corners(4,1)-corners(4,2)*corners(2,1))/dble(corners(4,1)-corners(2,1))

a4=dble(corners(3,2)-corners(4,2))/dble(corners(3,1)-corners(4,1))
b4=dble(corners(3,2)*corners(4,1)-corners(4,2)*corners(3,1))/dble(corners(4,1)-corners(3,1))
omask(:,:)=0
write(*,*) a1,b1,a2,b2,a3,b3,a4,b4
write(*,*) nline,ncol
do j=1, nline
   do i=1, ncol
      y1=dble(-j)*a1+b1
      y4=dble(-j)*a4+b4
      if((y1+i)*(y4+i) >=0 ) cycle   
      y2=dble(-j)*a2+b2
      y3=dble(-j)*a3+b3
      if((y2+i)*(y3+i) < 0 )  then 
          omask(i,j)=1
      endif
   end do
end do
!omask=0
!omask(200:300,40:60)=1
omask(:,:)=omask(:,:)*imask(:,:)
end subroutine maskoff

subroutine nns(imask,nline,ncol,tflag,onns, pairindex)
implicit none
integer*4 :: nline, ncol
integer*8 :: tflag
integer*4,dimension(1:ncol,1:nline), intent(in)  :: imask
real*4,   dimension(1:tflag), intent(out) :: onns
integer*4, dimension(1:tflag), intent(out):: pairindex 
!real*4, dimension(1:(tflag*(tflag-1)/2)), intent(out) :: onns

!f2py intent(in) :: imask, tflag
!f2py intent(hide), depend(imask) :: nline = shape(imask,0), ncol = shape(imask,1)
!f2py intent(out) :: onns, pairindex

integer*8                                    :: i,j,cnt
real, dimension(1:tflag)                   :: ncloud
real*8, dimension(1:tflag)                   :: xmass
real*8, dimension(1:tflag)                   :: ymass
real                                       :: cindex
real*8                                     :: temp, dis,mins

!onns=0
if (tflag <2) stop 'the number of clouds must be larger than 2'
xmass=0
ymass=0
ncloud=0
cnt=0
Do j=1, nline
   Do i=1, ncol
      if ( imask(i,j) <1) cycle
      cindex=imask(i,j)
      ncloud(cindex)=ncloud(cindex)+1.0
      xmass(cindex)=xmass(cindex)+i
      ymass(cindex)=ymass(cindex)+j
      cnt=cnt+1
   End do
End do
xmass(:)=xmass(:)/dble(ncloud(:))
ymass(:)=ymass(:)/dble(ncloud(:))
cnt=0
!open(30,file='nns.txt', action='write')
Do i=1, tflag-1
   onns(i)=((xmass(i)-xmass(i+1))*(xmass(i)-xmass(i+1))+ &
                 & (ymass(i)-ymass(i+1))*(ymass(i)-ymass(i+1)))
   pairindex(i)=i+1
   do j=1, tflag
      if ( i==j) cycle
      dis=((xmass(i)-xmass(j))*(xmass(i)-xmass(j))+ &
          & (ymass(i)-ymass(j))*(ymass(i)-ymass(j)))
      if ( dis < onns(i)) then 
         onns(i)=dis
         pairindex(i)=j
      end if
   end do
end do
onns(tflag)=((xmass(tflag)-xmass(1))*(xmass(tflag)-xmass(1))+ &
          & (ymass(tflag)-ymass(1))*(ymass(tflag)-ymass(1)))
pairindex(tflag)=1
do i=2, tflag-1
   dis=((xmass(i)-xmass(tflag))*(xmass(i)-xmass(tflag))+ &
          & (ymass(i)-ymass(tflag))*(ymass(i)-ymass(tflag)))
   if ( dis < onns(tflag)) then
       onns(tflag)= dis 
       pairindex(tflag)=i
   end if  
end do
onns(:)=sqrt(onns(:))
!Do i=1, tflag-1
!   Do j=i+1, tflag
!      cnt=cnt+1
!      temp=(xmass(i)-xmass(j))*(xmass(i)-xmass(j))+ &
!                 & (ymass(i)-ymass(j))*(ymass(i)-ymass(j))
!      write(30, FMT='(F10.1)') sqrt(temp)
!      onns(cnt)=sqrt(temp)
!      write(*,*) i,j, onns(cnt), xmass(i),ymass(i),xmass(j),ymass(j)
!   end do
!End do
!do i=1, tflag
!   write(30, FMT='(F10.4)') sqrt(onns(i))
!end do
!close (30)
end subroutine nns             

SUBROUTINE FLAG_EACH_CLOUD(IN, NLINE, NCOL, OUT, TFLAG, number)
!tflag is the number of the clouds
!out   is the output mask 
!bcpixel is the number of the boundary-cloud pixels. 
 implicit none 
 integer*1, dimension(1:ncol, 1:nline)             ::  in
 integer,                               intent(in) :: nline, ncol
 integer*4, dimension(1:ncol, 1:nline), intent(out):: out
 integer*8,                             intent(out):: tflag
 integer*8                                         :: number

 !f2py intent(in) :: in
 !f2py intent(hide), depend(in) :: nline = shape(in,0), ncol = shape(in,1)
 !f2py intent(out) :: out, tflag, number

 integer*8   :: i,j,k, temp, m1, m2, ir
 integer*8   :: flag, cnt, index1, index2
 integer*8,  dimension(:),     allocatable :: recd 

!-----------First Scan----------------
       flag=1
       out=0
       DO J=1, NLINE
          cnt=0
          Do I=1, NCOL
             IF (in(I,J)==1 .or. in(I,J)==2 )THEN
                out(i,J)=flag
                cnt=0
             ELSE 
                out(i,j)=0
                cnt=1+cnt
                if(cnt==1) flag=flag+1
             END IF  
         END DO
      END DO
!----------Second Scan--------------
      ALLOCATE(recd(1:flag))
      recd=0
      DO i=1, NCOL
         DO j=1, nline-1
            IF(out(I,J)>0 .and. out(I,J+1) >0) then
!----------ulti(i,j)-------c
             temp=out(i,j)
             do while(recd(temp) .ne. 0)
                temp=recd(temp)
             end do
             m1=temp
!---------=ulti(i,j+1)-----c           
             temp=out(i,j+1)
             do while(recd(temp) .ne. 0)
                temp=recd(temp)
             end do
             m2=temp
             If( m2 > m1) recd(m2)=m1          
             If( m2 < m1) recd(m1)=m2   
           END IF
         END DO
      END DO
!-----Third Scan-------C
      DO j=1, nline 
         Do i=1, ncol
            if (out(i,j) < 1 )cycle
               temp=out(i,j)
            do while (recd(temp) .ne. 0)
               temp=recd(temp)
            end do
            out(i,j)=temp
          end do
      END DO
!-----Redefine boundary cloudy pixels------
! in(i,j)=0 means no retrieval 
!      recd=0
!      DO J=1, NLINE
!         Do I=2, NCOL-1
!           IF ((in(I-1,J)==0 .and. in(i,j)>0 .and. in(i,j)<3) .or.  &
!               (in(i+1,J)==0 .and. in(i,j)>0 .and. in(i,j)<3)) recd(out(i,j))=1
!         END DO
!      END DO
!      DO I=1, NCOL
!         Do J=2, NLINE-1
!           IF ((in(I,J-1)==0 .and. in(i,j)>0 .and. in(i,j)<3) .or.  &
!               (in(i,J+1)==0 .and. in(i,j)>0 .and. in(i,j)<3)) recd(out(i,j))=1
!         END DO
!      END DO
!      DO i=1, NCOL
!         if (in(i,1)>0 .and. in(i,1)<3) recd(out(i,1))=1
!         if (in(i,nline)>0 .and. in(i,nline)<3) recd(out(i,nline))=1
!      end do
      number=0
!return the number of boundary clouds
     DO J=1, NLINE
         Do I=1, NCOL
           IF (recd(out(i,j))==1) then
              out(i,j)=0
              number=number +1
           End if
         END DO
      END DO
!---------Relabel the clouds------------
      recd=0
      Do j=1, nline 
         Do i=1, ncol
            if (out(i,j) < 1) cycle
            recd(out(i,j))=recd(out(i,j))+1
         end do
      end do
      temp=0
      DO i=1, flag
         if(recd(i)<1) cycle
         recd(i)=temp+1 
         temp=temp+1
      end do
      Do j=1, nline 
         Do i=1, ncol
            if(out(i,j)<1) cycle
             out(i,j)=recd(out(i,j))
         end do
      end do
!return the value of tflag
      tflag=temp
      deallocate(recd)
end subroutine  flag_each_cloud       