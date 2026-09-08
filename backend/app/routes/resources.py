from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.models import UserModel
from app.schemas import DemoSeedResult, ReadmeImportRequest, ReadmeImportResult, Resource, ResourceCreate, ResourceUpdate, ScanResult
from app.services.readme_importer import extract_links_from_markdown
from app.services.auth import get_current_user, owner_key_for_user
from app.services.resource_store import store

router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("", response_model=list[Resource])
def list_resources(user: UserModel = Depends(get_current_user)) -> list[Resource]:
    return store.list_resources(owner_key_for_user(user))


@router.post("", response_model=Resource, status_code=status.HTTP_201_CREATED)
def create_resource(payload: ResourceCreate, user: UserModel = Depends(get_current_user)) -> Resource:
    return store.create_resource(payload, owner_key=owner_key_for_user(user))


@router.post("/scan-all", response_model=list[ScanResult])
async def scan_all_resources(user: UserModel = Depends(get_current_user)) -> list[ScanResult]:
    return await store.scan_all_resources(owner_key_for_user(user))


@router.post("/demo/seed", response_model=DemoSeedResult)
def seed_demo_resources(user: UserModel = Depends(get_current_user)) -> DemoSeedResult:
    return store.seed_demo_resources(owner_key_for_user(user))


@router.post("/imports/readme", response_model=ReadmeImportResult)
def import_readme_links(
    payload: ReadmeImportRequest,
    user: UserModel = Depends(get_current_user),
) -> ReadmeImportResult:
    return store.import_links(extract_links_from_markdown(payload.markdown), owner_key_for_user(user))


@router.get("/{resource_id}", response_model=Resource)
def get_resource(resource_id: int, user: UserModel = Depends(get_current_user)) -> Resource:
    resource = store.get_resource(resource_id, owner_key_for_user(user))
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return resource


@router.put("/{resource_id}", response_model=Resource)
def update_resource(
    resource_id: int,
    payload: ResourceUpdate,
    user: UserModel = Depends(get_current_user),
) -> Resource:
    resource = store.update_resource(resource_id, payload, owner_key_for_user(user))
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return resource


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(resource_id: int, user: UserModel = Depends(get_current_user)) -> Response:
    if not store.delete_resource(resource_id, owner_key_for_user(user)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{resource_id}/scan", response_model=ScanResult)
async def scan_resource(resource_id: int, user: UserModel = Depends(get_current_user)) -> ScanResult:
    scan = await store.scan_resource(resource_id, owner_key_for_user(user))
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return scan


@router.get("/{resource_id}/scans", response_model=list[ScanResult])
def list_scans(resource_id: int, user: UserModel = Depends(get_current_user)) -> list[ScanResult]:
    owner_key = owner_key_for_user(user)
    if not store.get_resource(resource_id, owner_key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return store.list_scans(resource_id, owner_key)
